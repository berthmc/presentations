"""Tests for source enrichment and digest synthesis."""

from unittest.mock import AsyncMock, patch

import pytest

from presentations.core.schemas import DigestEntry, SourceDigest
from presentations.llm.synthesis import _chunk_text, _merge_digests, digest_source_context
from presentations.services.source_enrichment import enrich_source_context


def test_chunk_text_splits_long_source() -> None:
    text = "x" * 20_000
    chunks = _chunk_text(text, chunk_size=8000)
    assert len(chunks) == 3
    assert sum(len(chunk) for chunk in chunks) == 20_000


def test_merge_digests_deduplicates_claims() -> None:
    merged = _merge_digests(
        [
            SourceDigest(facts=[DigestEntry(claim="Latency under 200ms", source_quote="200ms")]),
            SourceDigest(facts=[DigestEntry(claim="latency under 200ms", source_quote="duplicate")]),
            SourceDigest(facts=[DigestEntry(claim="Uses WebRTC", source_quote="WebRTC")]),
        ]
    )
    assert len(merged.facts) == 2


def test_source_digest_to_prompt_text() -> None:
    digest = SourceDigest(
        facts=[
            DigestEntry(
                claim="End-to-end latency target is 200ms",
                source_quote="200ms budget",
                slide_topic_hint="Performance",
            )
        ]
    )
    text = digest.to_prompt_text()
    assert "Structured source digest" in text
    assert "200ms" in text


@pytest.mark.asyncio
async def test_digest_source_context_merges_chunk_results() -> None:
    from presentations.config.settings import Settings

    settings = Settings(_env_file=None, DIGEST_CHUNK_CHARS=10, ENABLE_DIGEST_PHASE=True)
    provider = AsyncMock()
    provider.name = "ollama"
    provider.generate_json = AsyncMock(
        side_effect=[
            {"facts": [{"claim": "Chunk one fact", "source_quote": "one"}]},
            {"facts": [{"claim": "Chunk two fact", "source_quote": "two"}]},
            {"facts": [{"claim": "Chunk three fact", "source_quote": "three"}]},
        ]
    )
    router = AsyncMock()
    router.get_synthesis_providers = AsyncMock(return_value=[provider])

    with patch("presentations.llm.synthesis.LLMRouter", return_value=router):
        digest = await digest_source_context(
            "012345678901234567890",
            "Topic: Speech architecture",
            settings=settings,
        )

    assert len(digest.facts) == 3
    assert provider.generate_json.await_count == 3


@pytest.mark.asyncio
async def test_enrich_source_context_appends_context7_docs() -> None:
    from presentations.config.settings import Settings

    settings = Settings(
        _env_file=None,
        CONTEXT7_ENABLED=True,
        CONTEXT7_API_KEY="ctx7sk-test",
    )
    with patch(
        "presentations.services.source_enrichment.fetch_context7_docs",
        new=AsyncMock(return_value="--- Context7: WebRTC ---\nDocs"),
    ):
        result = await enrich_source_context(
            "Topic: Real-Time AI Speech-to-Speech Architecture",
            "PDF content",
            settings=settings,
        )

    assert result is not None
    assert "PDF content" in result
    assert "--- Context7: WebRTC ---" in result
