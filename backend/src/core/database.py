"""Engine async, sessões e contexto multi-tenant (RLS).

A aplicação conecta como `app_rw` (NOSUPERUSER) e seta `app.workspace_id` por transação
via `SET LOCAL`. As políticas RLS no PostgreSQL filtram por esse valor — rede de segurança
contra qualquer query que esqueça o filtro de tenant.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

# Workspace ativo da requisição corrente (setado pelo middleware/deps de tenancy).
current_workspace_id: ContextVar[str | None] = ContextVar("current_workspace_id", default=None)

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope(workspace_id: str | None = None) -> AsyncIterator[AsyncSession]:
    """Abre uma sessão transacional. Se houver tenant, aplica o contexto RLS.

    Faz commit no sucesso e rollback em exceção.
    """
    wid = workspace_id or current_workspace_id.get()
    async with SessionLocal() as session:
        async with session.begin():
            if wid:
                # set_config transação-local (true) — não vaza entre conexões do pool.
                await session.execute(
                    text("SELECT set_config('app.workspace_id', :wid, true)"),
                    {"wid": str(wid)},
                )
            yield session


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency FastAPI: sessão com contexto de tenant do ContextVar (se houver)."""
    async with session_scope() as session:
        yield session
