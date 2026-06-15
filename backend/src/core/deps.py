"""Dependências FastAPI: autenticação, resolução de tenant (RLS) e RBAC.

- `auth_ctx`    → rotas autenticadas sem tenant (perfil, criar/listar workspaces).
- `tenant_ctx`  → rotas de negócio: resolve o workspace ativo (header X-Workspace-Id),
                  valida a membership e abre a sessão já com o contexto RLS aplicado.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Membership, User
from .database import current_workspace_id, session_scope
from .exceptions import Forbidden, Unauthorized
from .security import decode_token

ROLE_RANK = {"guest": 0, "collaborator": 1, "manager": 2, "admin": 3}


def _bearer_user_id(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Token ausente")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise Unauthorized("Token inválido") from None
    if payload.get("type") != "access":
        raise Unauthorized("Tipo de token inválido")
    return payload["sub"]


@dataclass
class AuthCtx:
    db: AsyncSession
    user: User


@dataclass
class TenantCtx:
    db: AsyncSession
    user: User
    membership: Membership

    @property
    def workspace_id(self):
        return self.membership.workspace_id

    @property
    def role(self) -> str:
        return self.membership.role

    @property
    def membership_id(self):
        return self.membership.id

    def require(self, *roles: str) -> None:
        """Exige um dos papéis (ou superior por ranking)."""
        min_rank = min(ROLE_RANK[r] for r in roles)
        if ROLE_RANK.get(self.role, -1) < min_rank:
            raise Forbidden(f"Requer papel: {' ou '.join(roles)}")


async def auth_ctx(authorization: str | None = Header(default=None)) -> AsyncIterator[AuthCtx]:
    user_id = _bearer_user_id(authorization)
    async with session_scope() as db:
        user = await db.scalar(select(User).where(User.id == user_id))
        if not user or not user.is_active:
            raise Unauthorized("Usuário inválido")
        yield AuthCtx(db=db, user=user)


async def tenant_ctx(
    authorization: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None),
) -> AsyncIterator[TenantCtx]:
    user_id = _bearer_user_id(authorization)
    if not x_workspace_id:
        raise Forbidden("Header X-Workspace-Id obrigatório")

    current_workspace_id.set(x_workspace_id)
    async with session_scope(workspace_id=x_workspace_id) as db:
        user = await db.scalar(select(User).where(User.id == user_id))
        if not user or not user.is_active:
            raise Unauthorized("Usuário inválido")
        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.workspace_id == x_workspace_id,
                Membership.status == "active",
            )
        )
        if not membership:
            raise Forbidden("Você não pertence a este workspace")
        yield TenantCtx(db=db, user=user, membership=membership)


# Açúcar para RBAC declarativo: Depends(require_role("manager"))
def require_role(*roles: str):
    async def _dep(ctx: TenantCtx = Depends(tenant_ctx)) -> TenantCtx:
        ctx.require(*roles)
        return ctx

    return _dep
