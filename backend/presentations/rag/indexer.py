"""Index source documents into Qdrant."""

from loguru import logger

from presentations.config.settings import Settings, get_settings
from presentations.rag import qdrant_store
from presentations.rag.embeddings import embed_texts


def chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into fixed-size chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += chunk_size
    return chunks


async def index_document(
    doc_id: str,
    text: str,
    *,
    settings: Settings | None = None,
) -> int:
    """Chunk, embed, and upsert a document into Qdrant.

    Args:
        doc_id: Stable document identifier.
        text: Full document text (Markdown).
        settings: Optional settings override.

    Returns:
        Number of chunks indexed.
    """
    settings = settings or get_settings()
    if not text.strip():
        return 0

    if not qdrant_store.is_available(settings=settings):
        logger.warning("Qdrant unavailable; skipping indexing for {}", doc_id)
        return 0

    chunks = chunk_text(text.strip(), settings.rag_chunk_chars)
    try:
        vectors = await embed_texts(chunks, settings=settings)
    except RuntimeError:
        logger.warning("Embedding failed; skipping indexing for {}", doc_id)
        return 0

    qdrant_store.upsert_chunks(doc_id, chunks, vectors, settings=settings)
    return len(chunks)
