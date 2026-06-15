"""Serviço de conhecimento: chunking, indexação e busca semântica (RAG)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Chunk, Document
from ...integrations.ollama import ollama


def chunk_text(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    """Chunking simples por caracteres com sobreposição (aprox. tokens)."""
    text = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


async def index_document(db: AsyncSession, document: Document, raw_text: str) -> int:
    """Cria chunks + embeddings para um documento. Retorna a quantidade de chunks."""
    pieces = chunk_text(raw_text)
    for i, piece in enumerate(pieces):
        embedding = await ollama.embed(piece)
        db.add(
            Chunk(
                workspace_id=document.workspace_id,
                document_id=document.id,
                ord=i,
                content=piece,
                token_count=max(1, len(piece) // 4),
                embedding=embedding,
            )
        )
    return len(pieces)


async def search(
    db: AsyncSession, query: str, top_k: int = 6, project_id: str | None = None
) -> list[dict]:
    """Busca semântica sob RLS (o tenant já está no contexto da sessão)."""
    qvec = await ollama.embed(query)
    distance = Chunk.embedding.cosine_distance(qvec)
    stmt = select(Chunk, distance.label("dist")).order_by(distance).limit(top_k)
    if project_id:
        stmt = stmt.join(Document, Document.id == Chunk.document_id).where(
            Document.project_id == project_id
        )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "document_id": str(c.document_id),
            "content": c.content,
            "score": round(1 - float(dist), 4),
        }
        for (c, dist) in rows
    ]
