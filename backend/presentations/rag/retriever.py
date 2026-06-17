"""Retrieve verified research snippets from Qdrant."""

from loguru import logger

from presentations.config.settings import Settings, get_settings
from presentations.core.state import ResearchPayload, ResearchSnippet
from presentations.rag import qdrant_store
from presentations.rag.embeddings import embed_query


async def retrieve_research_snippets(
    query: str,
    *,
    doc_id: str | None = None,
    settings: Settings | None = None,
) -> ResearchPayload:
    """Query Qdrant and return structured research snippets.

    Args:
        query: Brief or topic to retrieve against.
        doc_id: Optional filter to a single indexed document.
        settings: Optional settings override.

    Returns:
        ResearchPayload with top-k verified snippets.
    """
    settings = settings or get_settings()
    if not settings.rag_enabled or not qdrant_store.is_available(settings=settings):
        logger.info("RAG retrieval skipped (disabled or Qdrant unavailable)")
        return ResearchPayload()

    try:
        query_vector = await embed_query(query, settings=settings)
    except RuntimeError:
        return ResearchPayload()

    hits = qdrant_store.search(
        query_vector,
        top_k=settings.rag_top_k,
        doc_id=doc_id,
        settings=settings,
    )
    snippets = [
        ResearchSnippet(
            claim=hit["text"][:500],
            source_quote=hit["text"],
            doc_id=str(hit.get("doc_id", "")),
            score=float(hit.get("score", 0.0)),
            metadata={"chunk_index": hit.get("chunk_index", 0)},
        )
        for hit in hits
        if hit.get("text")
    ]
    return ResearchPayload(snippets=snippets)
