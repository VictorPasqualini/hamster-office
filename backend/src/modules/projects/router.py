from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.deps import TenantCtx, tenant_ctx
from ...core.events import record_audit
from ...core.exceptions import NotFound
from ...db.models import Agent, Project, ProjectAgent, ProjectMember
from .schemas import AgentAssign, ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=str(p.id),
        name=p.name,
        client_name=p.client_name,
        description=p.description,
        status=p.status,
    )


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("collaborator")
    p = Project(
        workspace_id=ctx.workspace_id,
        name=body.name,
        client_name=body.client_name,
        description=body.description,
        owner_membership_id=ctx.membership_id,
    )
    ctx.db.add(p)
    await ctx.db.flush()
    ctx.db.add(
        ProjectMember(
            project_id=p.id,
            membership_id=ctx.membership_id,
            workspace_id=ctx.workspace_id,
            project_role="lead",
        )
    )
    await record_audit(
        ctx.db,
        workspace_id=ctx.workspace_id,
        type_="project.created",
        actor_kind="user",
        actor_id=ctx.membership_id,
        target_kind="project",
        target_id=p.id,
        payload={"name": p.name},
    )
    return _out(p)


@router.get("", response_model=list[ProjectOut])
async def list_projects(ctx: TenantCtx = Depends(tenant_ctx)):
    rows = await ctx.db.scalars(
        select(Project).where(Project.status != "archived").order_by(Project.created_at.desc())
    )
    return [_out(p) for p in rows]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    p = await ctx.db.scalar(select(Project).where(Project.id == project_id))
    if not p:
        raise NotFound("Projeto não encontrado")
    return _out(p)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str, body: ProjectUpdate, ctx: TenantCtx = Depends(tenant_ctx)
):
    ctx.require("collaborator")
    p = await ctx.db.scalar(select(Project).where(Project.id == project_id))
    if not p:
        raise NotFound("Projeto não encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    return _out(p)


@router.post("/{project_id}/agents", status_code=201)
async def assign_agent(
    project_id: str, body: AgentAssign, ctx: TenantCtx = Depends(tenant_ctx)
):
    ctx.require("manager")
    p = await ctx.db.scalar(select(Project).where(Project.id == project_id))
    if not p:
        raise NotFound("Projeto não encontrado")
    agent = await ctx.db.scalar(select(Agent).where(Agent.id == body.agent_id))
    if not agent:
        raise NotFound("Agente não encontrado")
    exists = await ctx.db.scalar(
        select(ProjectAgent).where(
            ProjectAgent.project_id == project_id, ProjectAgent.agent_id == body.agent_id
        )
    )
    if not exists:
        ctx.db.add(
            ProjectAgent(
                project_id=p.id, agent_id=agent.id, workspace_id=ctx.workspace_id
            )
        )
    return {"ok": True}


@router.get("/{project_id}/agents")
async def project_agents(project_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    rows = (
        await ctx.db.execute(
            select(Agent)
            .join(ProjectAgent, ProjectAgent.agent_id == Agent.id)
            .where(ProjectAgent.project_id == project_id)
        )
    ).scalars()
    return [{"id": str(a.id), "name": a.name, "type": a.type} for a in rows]
