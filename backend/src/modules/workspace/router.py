from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.deps import AuthCtx, TenantCtx, auth_ctx, tenant_ctx
from ...core.exceptions import Conflict, NotFound
from ...db.models import Membership, User, Workspace, WorkspaceSettings
from .schemas import (
    MemberAdd,
    MemberOut,
    RoleChange,
    SettingsOut,
    WorkspaceCreate,
    WorkspaceOut,
)

router = APIRouter(prefix="/workspaces", tags=["workspace"])

VALID_ROLES = {"admin", "manager", "collaborator", "guest"}


@router.post("", response_model=WorkspaceOut, status_code=201)
async def create_workspace(body: WorkspaceCreate, ctx: AuthCtx = Depends(auth_ctx)):
    if await ctx.db.scalar(select(Workspace).where(Workspace.slug == body.slug)):
        raise Conflict("Slug já em uso")
    ws = Workspace(name=body.name, slug=body.slug, owner_user_id=ctx.user.id, plan="free")
    ctx.db.add(ws)
    await ctx.db.flush()
    ctx.db.add(WorkspaceSettings(workspace_id=ws.id))
    ctx.db.add(
        Membership(workspace_id=ws.id, user_id=ctx.user.id, role="admin", status="active")
    )
    return WorkspaceOut(id=str(ws.id), slug=ws.slug, name=ws.name, plan=ws.plan, role="admin")


@router.get("", response_model=list[WorkspaceOut])
async def my_workspaces(ctx: AuthCtx = Depends(auth_ctx)):
    rows = (
        await ctx.db.execute(
            select(Workspace, Membership.role)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == ctx.user.id, Membership.status == "active")
        )
    ).all()
    return [
        WorkspaceOut(id=str(w.id), slug=w.slug, name=w.name, plan=w.plan, role=role)
        for (w, role) in rows
    ]


@router.get("/current", response_model=WorkspaceOut)
async def current(ctx: TenantCtx = Depends(tenant_ctx)):
    ws = await ctx.db.scalar(select(Workspace).where(Workspace.id == ctx.workspace_id))
    return WorkspaceOut(id=str(ws.id), slug=ws.slug, name=ws.name, plan=ws.plan, role=ctx.role)


@router.get("/current/settings", response_model=SettingsOut)
async def get_settings(ctx: TenantCtx = Depends(tenant_ctx)):
    s = await ctx.db.scalar(
        select(WorkspaceSettings).where(WorkspaceSettings.workspace_id == ctx.workspace_id)
    )
    return SettingsOut(
        default_model=s.default_model,
        monthly_token_budget=s.monthly_token_budget,
        office_theme=s.office_theme,
    )


@router.get("/current/members", response_model=list[MemberOut])
async def members(ctx: TenantCtx = Depends(tenant_ctx)):
    rows = (
        await ctx.db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.workspace_id == ctx.workspace_id)
        )
    ).all()
    return [
        MemberOut(
            membership_id=str(m.id),
            user_id=str(u.id),
            name=u.name,
            email=u.email,
            role=m.role,
            status=m.status,
        )
        for (m, u) in rows
    ]


@router.post("/current/members", response_model=MemberOut, status_code=201)
async def add_member(body: MemberAdd, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("admin", "manager")
    if body.role not in VALID_ROLES:
        raise Conflict("Papel inválido")
    user = await ctx.db.scalar(select(User).where(User.email == body.email))
    if not user:
        raise NotFound("Usuário não encontrado (peça para se registrar primeiro)")
    existing = await ctx.db.scalar(
        select(Membership).where(
            Membership.workspace_id == ctx.workspace_id, Membership.user_id == user.id
        )
    )
    if existing:
        raise Conflict("Usuário já é membro")
    m = Membership(
        workspace_id=ctx.workspace_id, user_id=user.id, role=body.role, status="active"
    )
    ctx.db.add(m)
    await ctx.db.flush()
    return MemberOut(
        membership_id=str(m.id),
        user_id=str(user.id),
        name=user.name,
        email=user.email,
        role=m.role,
        status=m.status,
    )


@router.patch("/current/members/{membership_id}", response_model=MemberOut)
async def change_role(
    membership_id: str, body: RoleChange, ctx: TenantCtx = Depends(tenant_ctx)
):
    ctx.require("admin")
    if body.role not in VALID_ROLES:
        raise Conflict("Papel inválido")
    m = await ctx.db.scalar(
        select(Membership).where(
            Membership.id == membership_id, Membership.workspace_id == ctx.workspace_id
        )
    )
    if not m:
        raise NotFound("Membro não encontrado")
    m.role = body.role
    u = await ctx.db.scalar(select(User).where(User.id == m.user_id))
    return MemberOut(
        membership_id=str(m.id),
        user_id=str(u.id),
        name=u.name,
        email=u.email,
        role=m.role,
        status=m.status,
    )
