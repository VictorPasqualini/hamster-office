"""Auditoria leve: grava eventos em audit.audit_log na mesma sessão do caso de uso."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def record_audit(
    session: AsyncSession,
    *,
    workspace_id,
    type_: str,
    actor_kind: str,
    actor_id=None,
    target_kind: str | None = None,
    target_id=None,
    payload: dict | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO audit.audit_log
                (id, workspace_id, type, actor_kind, actor_id, target_kind, target_id, payload)
            VALUES
                (gen_random_uuid(), :ws, :type, :ak, :aid, :tk, :tid, CAST(:payload AS jsonb))
            """
        ),
        {
            "ws": str(workspace_id) if workspace_id else None,
            "type": type_,
            "ak": actor_kind,
            "aid": str(actor_id) if actor_id else None,
            "tk": target_kind,
            "tid": str(target_id) if target_id else None,
            "payload": __import__("json").dumps(payload or {}),
        },
    )
