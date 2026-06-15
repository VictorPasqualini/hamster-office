"""Dashboard administrativo: visão geral, consumo (tokens/custo) e auditoria.

Acesso restrito a manager+ (custos/auditoria são informações sensíveis).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from ...core.deps import TenantCtx, tenant_ctx
from ...db.models import (
    Agent,
    AgentRun,
    AuditLog,
    Document,
    Membership,
    Project,
    Task,
    UsageDaily,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
async def overview(ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("manager")
    ws = ctx.workspace_id

    async def _count(model, *where):
        return await ctx.db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    members = await _count(Membership, Membership.workspace_id == ws, Membership.status == "active")
    projects = await _count(Project, Project.status != "archived")
    open_tasks = await _count(Task, Task.status.notin_(["done", "canceled"]))
    agents = await _count(Agent)
    documents = await _count(Document)
    runs = await _count(AgentRun)

    totals = (
        await ctx.db.execute(
            select(
                func.coalesce(func.sum(AgentRun.prompt_tokens + AgentRun.completion_tokens), 0),
                func.coalesce(func.sum(AgentRun.cost_usd), 0),
            )
        )
    ).one()

    return {
        "members": members,
        "projects": projects,
        "open_tasks": open_tasks,
        "agents": agents,
        "documents": documents,
        "agent_runs": runs,
        "total_tokens": int(totals[0]),
        "total_cost_usd": float(totals[1]),
    }


@router.get("/usage")
async def usage(ctx: TenantCtx = Depends(tenant_ctx)):
    """Consumo por agente (tokens, custo, execuções)."""
    ctx.require("manager")
    rows = (
        await ctx.db.execute(
            select(
                Agent.id,
                Agent.name,
                Agent.type,
                func.coalesce(func.sum(UsageDaily.total_tokens), 0),
                func.coalesce(func.sum(UsageDaily.total_cost_usd), 0),
                func.coalesce(func.sum(UsageDaily.run_count), 0),
            )
            .outerjoin(UsageDaily, UsageDaily.agent_id == Agent.id)
            .group_by(Agent.id, Agent.name, Agent.type)
            .order_by(Agent.name)
        )
    ).all()
    return [
        {
            "agent_id": str(aid),
            "name": name,
            "type": type_,
            "total_tokens": int(tokens),
            "total_cost_usd": float(cost),
            "run_count": int(runs),
        }
        for (aid, name, type_, tokens, cost, runs) in rows
    ]


@router.get("/audit")
async def audit(limit: int = 50, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("manager")
    rows = await ctx.db.scalars(
        select(AuditLog)
        .where(AuditLog.workspace_id == ctx.workspace_id)
        .order_by(AuditLog.occurred_at.desc())
        .limit(min(limit, 200))
    )
    return [
        {
            "id": str(e.id),
            "type": e.type,
            "actor_kind": e.actor_kind,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "target_kind": e.target_kind,
            "target_id": str(e.target_id) if e.target_id else None,
            "payload": e.payload,
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        }
        for e in rows
    ]
