"""Local embedding generation via Ollama."""

import httpx
from loguru import logger

from presentations.config.settings import Settings, get_settings


async def embed_texts(texts: list[str], *, settings: Settings | None = None) -> list[list[float]]:
    """Generate embeddings for a batch of texts using Ollama.

    Args:
        texts: Input strings to embed.
        settings: Optional settings override.

    Returns:
        List of embedding vectors aligned with input texts.
    """
    settings = settings or get_settings()
    if not texts:
        return []

    host = settings.ollama_host.rstrip("/")
    model = settings.embedding_model
    vectors: list[list[float]] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for text in texts:
            payload = {"model": model, "prompt": text}
            try:
                response = await client.post(f"{host}/api/embeddings", json=payload)
                response.raise_for_status()
                body = response.json()
                vectors.append(body["embedding"])
            except httpx.HTTPError as exc:
                logger.warning("Embedding request failed for chunk (model={}): {}", model, exc)
                raise RuntimeError(f"Ollama embedding failed for model {model}") from exc

    return vectors


async def embed_query(query: str, *, settings: Settings | None = None) -> list[float]:
    """Embed a single query string."""
    vectors = await embed_texts([query], settings=settings)
    return vectors[0]
