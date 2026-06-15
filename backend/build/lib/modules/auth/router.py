from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import AuthCtx, auth_ctx
from ...core.exceptions import Conflict, Unauthorized
from ...core.security import (
    create_access_token,
    hash_token,
    new_refresh_token,
    refresh_expiry,
    verify_password,
    hash_password,
)
from ...db.models import Membership, RefreshToken, User, Workspace
from .schemas import LoginIn, MeOut, RefreshIn, RegisterIn, TokenOut, UserOut, WorkspaceBrief

router = APIRouter(prefix="/auth", tags=["auth"])


async def _workspaces_of(db: AsyncSession, user_id) -> list[WorkspaceBrief]:
    rows = (
        await db.execute(
            select(Workspace.id, Workspace.slug, Workspace.name, Membership.role)
            .join(Membership, Membership.workspace_id == Workspace.id)
            .where(Membership.user_id == user_id, Membership.status == "active")
        )
    ).all()
    return [
        WorkspaceBrief(id=str(i), slug=s, name=n, role=r) for (i, s, n, r) in rows
    ]


async def _issue_tokens(db: AsyncSession, user: User) -> TokenOut:
    access = create_access_token(str(user.id))
    raw, hashed = new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=hashed, expires_at=refresh_expiry()))
    workspaces = await _workspaces_of(db, user.id)
    return TokenOut(access_token=access, refresh_token=raw, workspaces=workspaces)


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise Conflict("Email já cadastrado")
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()
    return await _issue_tokens(db, user)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise Unauthorized("Credenciais inválidas")
    user.last_login_at = datetime.now(UTC)
    return await _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    hashed = hash_token(body.refresh_token)
    rt = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hashed))
    if not rt or rt.revoked_at is not None or rt.expires_at < datetime.now(UTC):
        raise Unauthorized("Refresh token inválido")
    rt.revoked_at = datetime.now(UTC)  # rotação
    user = await db.scalar(select(User).where(User.id == rt.user_id))
    return await _issue_tokens(db, user)


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    hashed = hash_token(body.refresh_token)
    rt = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hashed))
    if rt:
        rt.revoked_at = datetime.now(UTC)


@router.get("/me", response_model=MeOut)
async def me(ctx: AuthCtx = Depends(auth_ctx)):
    return MeOut(
        user=UserOut(
            id=str(ctx.user.id),
            email=ctx.user.email,
            name=ctx.user.name,
            avatar_url=ctx.user.avatar_url,
        ),
        workspaces=await _workspaces_of(ctx.db, ctx.user.id),
    )
