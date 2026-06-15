from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.deps import TenantCtx, tenant_ctx
from ...core.exceptions import AppError, NotFound
from ...core.queue import enqueue
from ...db.models import Agent, AgentRun
from .schemas import (
    AGENT_TYPES,
    AVAILABLE_TOOLS,
    AgentCreate,
    AgentOut,
    AgentUpdate,
    ExecuteIn,
    RunOut,
)

router = APIRouter(prefix="/agents", tags=["agents"])
runs_router = APIRouter(prefix="/runs", tags=["agents"])


def _out(a: Agent) -> AgentOut:
    return AgentOut(
        id=str(a.id),
        name=a.name,
        type=a.type,
        persona=a.persona,
        model=a.model,
        temperature=float(a.temperature),
        tools=a.tools or [],
        is_active=a.is_active,
        appearance=a.appearance or {},
    )


def _run_out(r: AgentRun) -> RunOut:
    return RunOut(
        id=str(r.id),
        agent_id=str(r.agent_id),
        status=r.status,
        model=r.model,
        prompt_tokens=r.prompt_tokens,
        completion_tokens=r.completion_tokens,
        cost_usd=float(r.cost_usd),
        output=r.output,
        error=r.error,
    )


def _validate_tools(tools: list[str]) -> None:
    invalid = set(tools) - AVAILABLE_TOOLS
    if invalid:
        raise AppError(f"Tools inválidas: {', '.join(invalid)}")


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(body: AgentCreate, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("manager")
    if body.type not in AGENT_TYPES:
        raise AppError("Tipo de agente inválido")
    _validate_tools(body.tools)
    a = Agent(
        workspace_id=ctx.workspace_id,
        name=body.name,
        type=body.type,
        persona=body.persona,
        system_prompt=body.system_prompt,
        model=body.model,
        temperature=body.temperature,
        tools=body.tools,
        appearance=body.appearance,
    )
    ctx.db.add(a)
    await ctx.db.flush()
    return _out(a)


@router.get("", response_model=list[AgentOut])
async def list_agents(ctx: TenantCtx = Depends(tenant_ctx)):
    rows = await ctx.db.scalars(select(Agent).order_by(Agent.created_at))
    return [_out(a) for a in rows]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    a = await ctx.db.scalar(select(Agent).where(Agent.id == agent_id))
    if not a:
        raise NotFound("Agente não encontrado")
    return _out(a)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: str, body: AgentUpdate, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("manager")
    a = await ctx.db.scalar(select(Agent).where(Agent.id == agent_id))
    if not a:
        raise NotFound("Agente não encontrado")
    data = body.model_dump(exclude_unset=True)
    if "tools" in data:
        _validate_tools(data["tools"])
    for field, value in data.items():
        setattr(a, field, value)
    return _out(a)


@router.post("/{agent_id}/execute", response_model=RunOut, status_code=202)
async def execute_agent(agent_id: str, body: ExecuteIn, ctx: TenantCtx = Depends(tenant_ctx)):
    a = await ctx.db.scalar(select(Agent).where(Agent.id == agent_id))
    if not a:
        raise NotFound("Agente não encontrado")
    run = AgentRun(
        workspace_id=ctx.workspace_id,
        agent_id=a.id,
        project_id=body.project_id,
        room_id=body.room_id,
        trigger_kind="api",
        status="queued",
        model=a.model,
    )
    ctx.db.add(run)
    await ctx.db.flush()
    await enqueue("run_agent", str(run.id), str(ctx.workspace_id), body.prompt)
    return _run_out(run)


@router.get("/{agent_id}/runs", response_model=list[RunOut])
async def agent_runs(agent_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    rows = await ctx.db.scalars(
        select(AgentRun)
        .where(AgentRun.agent_id == agent_id)
        .order_by(AgentRun.created_at.desc())
        .limit(50)
    )
    return [_run_out(r) for r in rows]


@runs_router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    r = await ctx.db.scalar(select(AgentRun).where(AgentRun.id == run_id))
    if not r:
        raise NotFound("Execução não encontrada")
    return _run_out(r)
