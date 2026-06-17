"""Qdrant vector store for research document chunks."""

from typing import Any
from uuid import uuid4

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from presentations.config.settings import Settings, get_settings

_VECTOR_SIZE = 1024


def _get_client(settings: Settings | None = None) -> QdrantClient:
    """Return a Qdrant client for the configured URL."""
    settings = settings or get_settings()
    return QdrantClient(url=settings.qdrant_url, timeout=10)


def ensure_collection(*, settings: Settings | None = None, vector_size: int = _VECTOR_SIZE) -> None:
    """Create the research collection if it does not exist."""
    settings = settings or get_settings()
    client = _get_client(settings)
    collection = settings.qdrant_collection
    existing = {item.name for item in client.get_collections().collections}
    if collection in existing:
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    logger.info("Created Qdrant collection {}", collection)


def upsert_chunks(
    doc_id: str,
    chunks: list[str],
    vectors: list[list[float]],
    *,
    settings: Settings | None = None,
) -> None:
    """Upsert document chunks with embeddings into Qdrant."""
    settings = settings or get_settings()
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors length mismatch")

    ensure_collection(settings=settings, vector_size=len(vectors[0]) if vectors else _VECTOR_SIZE)
    client = _get_client(settings)
    points = [
        PointStruct(
            id=str(uuid4()),
            vector=vector,
            payload={"doc_id": doc_id, "text": chunk, "chunk_index": index},
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]
    if points:
        client.upsert(collection_name=settings.qdrant_collection, points=points)
        logger.info("Indexed {} chunks for doc {}", len(points), doc_id)


def search(
    query_vector: list[float],
    *,
    top_k: int,
    doc_id: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Search Qdrant for nearest chunks."""
    settings = settings or get_settings()
    client = _get_client(settings)
    query_filter = None
    if doc_id:
        query_filter = Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))])

    try:
        results = client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )
    except Exception as exc:
        logger.warning("Qdrant search failed: {}", exc)
        return []

    return [
        {
            "text": hit.payload.get("text", ""),
            "doc_id": hit.payload.get("doc_id", ""),
            "score": hit.score,
            "chunk_index": hit.payload.get("chunk_index", 0),
        }
        for hit in results
    ]


def is_available(*, settings: Settings | None = None) -> bool:
    """Return True when Qdrant responds to a health check."""
    settings = settings or get_settings()
    try:
        client = _get_client(settings)
        client.get_collections()
        return True
    except Exception:
        return False
