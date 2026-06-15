"""Lógica de chat reutilizável por REST, WebSocket e workers."""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.queue import enqueue
from ...core.realtime import publish_event
from ...db.models import Agent, AgentRun, Message, Participant

MENTION_RE = re.compile(r"@([\wÀ-ÿ]+)")


def msg_dict(m: Message) -> dict:
    return {
        "id": str(m.id),
        "room_id": str(m.room_id),
        "author_kind": m.author_kind,
        "author_id": str(m.author_id) if m.author_id else None,
        "content": m.content,
        "parent_id": str(m.parent_id) if m.parent_id else None,
        "agent_run_id": str(m.agent_run_id) if m.agent_run_id else None,
        "mentions": m.mentions,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def agents_in_room(db: AsyncSession, room_id) -> list[Agent]:
    rows = await db.execute(
        select(Agent)
        .join(Participant, Participant.member_id == Agent.id)
        .where(Participant.room_id == room_id, Participant.member_kind == "agent")
    )
    return list(rows.scalars())


async def detect_mentions(db: AsyncSession, room_id, content: str) -> list[Agent]:
    """Retorna os agentes da sala mencionados via @Nome (case-insensitive)."""
    names = {n.lower() for n in MENTION_RE.findall(content)}
    if not names:
        return []
    return [a for a in await agents_in_room(db, room_id) if a.name.lower() in names]


async def post_message(
    db: AsyncSession,
    *,
    workspace_id,
    room_id,
    author_kind: str,
    author_id,
    content: str,
    mentions: list | None = None,
    agent_run_id=None,
    parent_id=None,
    publish: bool = True,
) -> Message:
    m = Message(
        workspace_id=workspace_id,
        room_id=room_id,
        author_kind=author_kind,
        author_id=author_id,
        content=content,
        mentions=mentions or [],
        agent_run_id=agent_run_id,
        parent_id=parent_id,
    )
    db.add(m)
    await db.flush()
    if publish:
        await publish_event(f"room:{room_id}", "chat.message.created", msg_dict(m))
    return m


async def handle_user_message(
    db: AsyncSession, *, workspace_id, room_id, author_id, content: str, parent_id=None
) -> Message:
    """Persiste a mensagem do usuário e dispara agentes mencionados."""
    mentioned = await detect_mentions(db, room_id, content)
    mentions = [{"kind": "agent", "id": str(a.id), "name": a.name} for a in mentioned]
    m = await post_message(
        db,
        workspace_id=workspace_id,
        room_id=room_id,
        author_kind="user",
        author_id=author_id,
        content=content,
        mentions=mentions,
        parent_id=parent_id,
    )

    for agent in mentioned:
        run = AgentRun(
            workspace_id=workspace_id,
            agent_id=agent.id,
            room_id=room_id,
            trigger_kind="chat_mention",
            trigger_ref=m.id,
            status="queued",
            model=agent.model,
        )
        db.add(run)
        await db.flush()
        await enqueue("run_agent", str(run.id), str(workspace_id))
    return m
