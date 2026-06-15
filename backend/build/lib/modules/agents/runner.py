"""Execução de um agente (chamado pelos workers).

Fluxo (ReAct simplificado para o MVP):
  1. monta contexto: histórico recente da sala (memória curta) + RAG (se tiver a tool search_kb)
  2. chama o LLM (Ollama, com fallback mock)
  3. registra tokens/custo/status no AgentRun
  4. posta a resposta de volta na sala (se houver) e atualiza billing/auditoria
"""

import logging
import time
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.realtime import publish_event
from ...db.models import Agent, AgentRun, Message
from ...integrations.ollama import ollama
from ..chat.service import post_message
from ..knowledge.service import search as kb_search

log = logging.getLogger("agent_runner")
HISTORY_LIMIT = 10
RAG_TOP_K = 4


async def _recent_history(db: AsyncSession, room_id) -> str:
    rows = await db.scalars(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    msgs = list(rows)
    msgs.reverse()
    lines = []
    for m in msgs:
        who = "Usuário" if m.author_kind == "user" else m.author_kind.capitalize()
        lines.append(f"{who}: {m.content}")
    return "\n".join(lines)


async def _bump_usage(db: AsyncSession, run: AgentRun) -> None:
    await db.execute(
        text(
            """
            INSERT INTO audit.usage_daily
                (workspace_id, day, agent_id, total_tokens, total_cost_usd, run_count)
            VALUES (:ws, :day, :agent, :tokens, :cost, 1)
            ON CONFLICT (workspace_id, day, agent_id) DO UPDATE SET
                total_tokens   = audit.usage_daily.total_tokens + EXCLUDED.total_tokens,
                total_cost_usd = audit.usage_daily.total_cost_usd + EXCLUDED.total_cost_usd,
                run_count      = audit.usage_daily.run_count + 1
            """
        ),
        {
            "ws": str(run.workspace_id),
            "day": date.today(),
            "agent": str(run.agent_id),
            "tokens": run.prompt_tokens + run.completion_tokens,
            "cost": float(run.cost_usd),
        },
    )


async def run_agent(db: AsyncSession, run: AgentRun, prompt: str | None = None) -> None:
    started = time.monotonic()
    agent = await db.scalar(select(Agent).where(Agent.id == run.agent_id))
    if not agent:
        run.status = "failed"
        run.error = "Agente não encontrado"
        return

    run.status = "running"
    await db.flush()
    await publish_event(
        f"run:{run.id}", "agent.run.started", {"run_id": str(run.id), "agent": agent.name}
    )

    # Mensagem que disparou (se via chat) ou prompt ad-hoc.
    if prompt is None and run.trigger_ref:
        trigger = await db.scalar(select(Message).where(Message.id == run.trigger_ref))
        prompt = trigger.content if trigger else ""
    prompt = prompt or ""

    # Memória curta + RAG
    history = await _recent_history(db, run.room_id) if run.room_id else ""
    rag_context = ""
    if "search_kb" in (agent.tools or []) and prompt.strip():
        try:
            chunks = await kb_search(db, prompt, RAG_TOP_K, str(run.project_id) if run.project_id else None)
            if chunks:
                rag_context = "\n\n".join(f"- {c['content'][:500]}" for c in chunks)
        except Exception as e:  # noqa: BLE001
            log.warning("RAG falhou: %s", e)

    system = agent.system_prompt
    if agent.persona:
        system += f"\n\nPersona: {agent.persona}"
    parts = []
    if rag_context:
        parts.append(f"Contexto da base de conhecimento:\n{rag_context}")
    if history:
        parts.append(f"Histórico recente da conversa:\n{history}")
    parts.append(f"Mensagem atual:\n{prompt}")
    user_prompt = "\n\n".join(parts)

    try:
        result = await ollama.chat(system, user_prompt)
    except Exception as e:  # noqa: BLE001
        run.status = "failed"
        run.error = str(e)
        await publish_event(f"run:{run.id}", "agent.run.failed", {"error": str(e)})
        return

    run.prompt_tokens = result["prompt_tokens"]
    run.completion_tokens = result["completion_tokens"]
    run.cost_usd = result["cost_usd"]
    run.output = result["content"]
    run.status = "completed"
    run.latency_ms = int((time.monotonic() - started) * 1000)

    if run.room_id:
        await post_message(
            db,
            workspace_id=run.workspace_id,
            room_id=run.room_id,
            author_kind="agent",
            author_id=agent.id,
            content=result["content"],
            agent_run_id=run.id,
        )

    await _bump_usage(db, run)
    await publish_event(
        f"run:{run.id}",
        "agent.run.completed",
        {
            "run_id": str(run.id),
            "total_tokens": run.prompt_tokens + run.completion_tokens,
            "cost_usd": float(run.cost_usd),
            "mocked": result.get("mocked", False),
        },
    )
