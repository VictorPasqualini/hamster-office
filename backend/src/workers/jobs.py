"""Jobs assíncronos (arq): processamento de documentos e execução de agentes."""

import io
import logging

from sqlalchemy import select

from ..core.database import session_scope
from ..core.events import record_audit
from ..core.observability import AGENT_COST, AGENT_RUNS, AGENT_TOKENS, DOCS_INDEXED
from ..db.models import AgentRun, Document
from ..integrations import storage
from ..modules.agents.runner import run_agent as _run_agent
from ..modules.knowledge.service import index_document

log = logging.getLogger("jobs")


def _extract_text(data: bytes, mime: str | None, key: str) -> str:
    is_pdf = (mime and "pdf" in mime) or key.lower().endswith(".pdf")
    if is_pdf:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:  # noqa: BLE001
            log.warning("Falha ao extrair PDF: %s", e)
            return ""
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


async def process_document(ctx, document_id: str, workspace_id: str) -> None:
    async with session_scope(workspace_id=workspace_id) as db:
        doc = await db.scalar(select(Document).where(Document.id == document_id))
        if not doc:
            return
        try:
            data = storage.get_bytes(doc.object_key)
            text = _extract_text(data, doc.mime, doc.object_key)
            if not text.strip():
                doc.status = "failed"
                return
            count = await index_document(db, doc, text)
            doc.status = "indexed"
            DOCS_INDEXED.inc()
            await record_audit(
                db,
                workspace_id=workspace_id,
                type_="knowledge.document.processed",
                actor_kind="system",
                target_kind="document",
                target_id=doc.id,
                payload={"chunks": count},
            )
            log.info("Documento %s indexado (%d chunks).", document_id, count)
        except Exception:  # noqa: BLE001
            log.exception("Falha ao processar documento %s", document_id)
            doc.status = "failed"


async def run_agent(ctx, run_id: str, workspace_id: str, prompt: str | None = None) -> None:
    async with session_scope(workspace_id=workspace_id) as db:
        run = await db.scalar(select(AgentRun).where(AgentRun.id == run_id))
        if not run:
            log.warning("Run %s não encontrado.", run_id)
            return
        await _run_agent(db, run, prompt)
        AGENT_RUNS.labels(run.status).inc()
        AGENT_TOKENS.inc(run.prompt_tokens + run.completion_tokens)
        AGENT_COST.inc(float(run.cost_usd))
