import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.deps import TenantCtx, tenant_ctx
from ...core.exceptions import NotFound
from ...core.queue import enqueue
from ...db.models import Document
from ...integrations import storage
from .schemas import DocumentOut, SearchIn, UploadUrlIn, UploadUrlOut
from .service import search as kb_search

documents_router = APIRouter(prefix="/documents", tags=["documents"])
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=str(d.id),
        title=d.title,
        mime=d.mime,
        status=d.status,
        project_id=str(d.project_id) if d.project_id else None,
    )


@documents_router.post("/upload-url", response_model=UploadUrlOut)
async def upload_url(body: UploadUrlIn, ctx: TenantCtx = Depends(tenant_ctx)):
    ctx.require("collaborator")
    doc_id = uuid.uuid4()
    key = storage.object_key(str(ctx.workspace_id), str(doc_id), body.filename)
    d = Document(
        id=doc_id,
        workspace_id=ctx.workspace_id,
        project_id=body.project_id,
        title=body.title or body.filename,
        object_key=key,
        mime=body.mime,
        status="uploaded",
        uploaded_by=ctx.membership_id,
    )
    ctx.db.add(d)
    await ctx.db.flush()
    return UploadUrlOut(
        document_id=str(doc_id), object_key=key, upload_url=storage.presigned_put(key)
    )


@documents_router.post("/{document_id}/process", status_code=202)
async def process(document_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    """Chamado após o upload concluir no MinIO: dispara extração + embeddings."""
    d = await ctx.db.scalar(select(Document).where(Document.id == document_id))
    if not d:
        raise NotFound("Documento não encontrado")
    d.status = "processing"
    await enqueue("process_document", str(document_id), str(ctx.workspace_id))
    return {"status": "processing"}


@documents_router.get("", response_model=list[DocumentOut])
async def list_documents(ctx: TenantCtx = Depends(tenant_ctx)):
    rows = await ctx.db.scalars(select(Document).order_by(Document.created_at.desc()))
    return [_out(d) for d in rows]


@documents_router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    d = await ctx.db.scalar(select(Document).where(Document.id == document_id))
    if not d:
        raise NotFound("Documento não encontrado")
    return _out(d)


@documents_router.get("/{document_id}/download-url")
async def download_url(document_id: str, ctx: TenantCtx = Depends(tenant_ctx)):
    d = await ctx.db.scalar(select(Document).where(Document.id == document_id))
    if not d:
        raise NotFound("Documento não encontrado")
    return {"download_url": storage.presigned_get(d.object_key)}


@knowledge_router.post("/search")
async def search(body: SearchIn, ctx: TenantCtx = Depends(tenant_ctx)):
    results = await kb_search(ctx.db, body.query, body.top_k, body.project_id)
    return {"chunks": results}
