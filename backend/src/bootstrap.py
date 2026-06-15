"""Bootstrap do banco — executado pelo serviço `migrate` (como superusuário).

Passos idempotentes:
  1. cria a role da aplicação (app_rw, NOSUPERUSER → sujeita a RLS)
  2. cria extensões (pgcrypto, vector, pg_trgm)
  3. cria os schemas
  4. cria todas as tabelas (metadata.create_all)
  5. concede privilégios à app_rw
  6. habilita RLS + política de tenant nas tabelas de negócio
  7. seed de dados demo (opcional, SEED_DEMO=true)

Rode com:  python -m src.bootstrap
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .core.config import settings
from .core.logging import setup_logging
from .db.base import Base
from .db.models import ALL_SCHEMAS, TENANT_TABLES  # noqa: F401 (registra os modelos)
from . import db  # noqa: F401

log = logging.getLogger("bootstrap")


async def _create_role(conn) -> None:
    await conn.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{settings.app_db_user}') THEN
                    CREATE ROLE {settings.app_db_user} LOGIN PASSWORD '{settings.app_db_password}'
                        NOSUPERUSER NOCREATEDB NOCREATEROLE;
                END IF;
            END $$;
            """
        )
    )


async def _extensions(conn) -> None:
    for ext in ("pgcrypto", "vector", "pg_trgm", "citext"):
        await conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))


async def _schemas(conn) -> None:
    for schema in ALL_SCHEMAS:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


async def _grants(conn) -> None:
    user = settings.app_db_user
    for schema in ALL_SCHEMAS:
        await conn.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO {user}'))
        await conn.execute(
            text(
                f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO {user}'
            )
        )
        await conn.execute(
            text(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "{schema}" TO {user}')
        )
        # privilégios padrão para tabelas futuras
        await conn.execute(
            text(
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {user}"
            )
        )


async def _rls(conn) -> None:
    """Habilita RLS e cria a política de isolamento por tenant."""
    await conn.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION public.current_workspace_id() RETURNS uuid AS $$
              SELECT NULLIF(current_setting('app.workspace_id', true), '')::uuid;
            $$ LANGUAGE sql STABLE;
            """
        )
    )
    for table in TENANT_TABLES:
        await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        await conn.execute(
            text(
                f"""
                CREATE POLICY tenant_isolation ON {table}
                  USING (workspace_id = public.current_workspace_id())
                  WITH CHECK (workspace_id = public.current_workspace_id())
                """
            )
        )


async def _vector_indexes(conn) -> None:
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw "
            "ON knowledge.chunks USING hnsw (embedding vector_cosine_ops)"
        )
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS messages_room_created ON chat.messages (room_id, created_at)")
    )


async def main() -> None:
    setup_logging()
    engine = create_async_engine(settings.database_superuser_url, future=True)
    async with engine.begin() as conn:
        log.info("Criando role da aplicação...")
        await _create_role(conn)
        log.info("Criando extensões...")
        await _extensions(conn)
        log.info("Criando schemas...")
        await _schemas(conn)
        log.info("Criando tabelas...")
        await conn.run_sync(Base.metadata.create_all)
        log.info("Concedendo privilégios...")
        await _grants(conn)
        log.info("Aplicando RLS...")
        await _rls(conn)
        log.info("Criando índices (HNSW etc.)...")
        await _vector_indexes(conn)
    await engine.dispose()

    if settings.seed_demo:
        from .seed import seed_demo

        log.info("Seed demo...")
        await seed_demo()

    log.info("Bootstrap concluído.")


if __name__ == "__main__":
    asyncio.run(main())
