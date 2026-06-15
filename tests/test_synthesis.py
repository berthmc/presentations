"""Tests for deck synthesis provider fallback and grounding prompts."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from presentations.core.schemas import DeckSpec, GenerationMode, LayoutEntry, LayoutProfile, PlaceholderInfo
from presentations.llm.synthesis import _build_user_prompt, synthesize_deck_spec


def test_build_user_prompt_includes_source_context() -> None:
    prompt = _build_user_prompt(
        brief="Topic: EU cloud adoption",
        layout=None,
        mode=GenerationMode.SCRATCH,
        source_context="# Report\n\nCloud spend rose 12%.",
    )
    assert "Brief:\nTopic: EU cloud adoption" in prompt
    assert "Source document (grounding reference):\n# Report" in prompt


def test_build_user_prompt_preserves_multi_document_separators() -> None:
    merged = (
        "--- Document: report-a.pdf ---\nCloud spend rose 12%.\n\n"
        "--- Document: report-b.pdf ---\nEU adoption accelerated."
    )
    prompt = _build_user_prompt(
        brief="Topic: EU cloud adoption",
        layout=None,
        mode=GenerationMode.SCRATCH,
        source_context=merged,
    )
    assert "--- Document: report-a.pdf ---" in prompt
    assert "--- Document: report-b.pdf ---" in prompt
    assert "Cloud spend rose 12%." in prompt
    assert "EU adoption accelerated." in prompt


def test_build_user_prompt_truncates_source_context_when_capped() -> None:
    long_source = "A" * 100
    prompt = _build_user_prompt(
        brief="Topic: EU cloud adoption",
        layout=None,
        mode=GenerationMode.SCRATCH,
        source_context=long_source,
        max_source_chars=40,
    )
    assert "Source document (grounding reference):\n" + ("A" * 40) in prompt
    assert "[Source truncated to 40 chars for local model]" in prompt
    assert "A" * 41 not in prompt


def test_build_user_prompt_no_truncation_note_without_cap() -> None:
    long_source = "B" * 100
    prompt = _build_user_prompt(
        brief="Topic: EU cloud adoption",
        layout=None,
        mode=GenerationMode.SCRATCH,
        source_context=long_source,
    )
    assert long_source in prompt
    assert "[Source truncated" not in prompt


def test_build_user_prompt_omits_source_when_none() -> None:
    prompt = _build_user_prompt(
        brief="Topic: EU cloud adoption",
        layout=None,
        mode=GenerationMode.SCRATCH,
        source_context=None,
    )
    assert "Source document" not in prompt


def test_build_user_prompt_uses_compact_layout() -> None:
    layout = LayoutProfile(
        source_path="/tmp/template.pptx",
        layouts={
            0: LayoutEntry(
                name="Title",
                placeholders=[PlaceholderInfo(index=0, name="title", type="TITLE")],
            )
        },
    )
    prompt = _build_user_prompt("Brief text", layout, GenerationMode.TEMPLATE)
    assert '"allowed_ph_idx"' in prompt
    assert '"ph_idx": 0' in prompt
    assert "source_path" not in prompt
    assert "theme" not in prompt


@pytest.mark.asyncio
async def test_synthesize_falls_back_to_gemini_after_ollama_fails() -> None:
    deck_payload = {
        "title": "Fallback Deck",
        "mode": "scratch",
        "slides": [{"layout_index": 0, "mappings": [{"ph_idx": 0, "content": "Hello"}]}],
    }
    ollama = MagicMock()
    ollama.name = "ollama"
    ollama.generate_json = AsyncMock(side_effect=ValueError("Ollama synthesis did not return valid JSON"))

    gemini = MagicMock()
    gemini.name = "gemini"
    gemini.model = "gemini-2.5-pro"
    gemini.generate_json = AsyncMock(return_value=deck_payload)

    router = MagicMock()
    router.get_synthesis_providers = AsyncMock(return_value=[ollama, gemini])

    with patch("presentations.llm.synthesis.LLMRouter", return_value=router):
        deck = await synthesize_deck_spec(
            brief="Topic: Test deck",
            mode=GenerationMode.SCRATCH,
            allow_cloud=True,
            max_retries=0,
        )

    assert isinstance(deck, DeckSpec)
    assert deck.title == "Fallback Deck"
    assert ollama.generate_json.await_count == 1
    assert gemini.generate_json.await_count == 1


@pytest.mark.asyncio
async def test_synthesize_raises_when_all_providers_fail() -> None:
    failing = MagicMock()
    failing.name = "ollama"
    failing.generate_json = AsyncMock(side_effect=ValueError("bad json"))

    gemini = MagicMock()
    gemini.name = "gemini"
    gemini.generate_json = AsyncMock(side_effect=ValueError("bad json"))

    router = MagicMock()
    router.get_synthesis_providers = AsyncMock(return_value=[failing, gemini])

    with patch("presentations.llm.synthesis.LLMRouter", return_value=router):
        with pytest.raises(ValueError, match="Failed to synthesize deck"):
            await synthesize_deck_spec(
                brief="Topic: Test",
                mode=GenerationMode.SCRATCH,
                allow_cloud=True,
                max_retries=0,
            )


@pytest.mark.asyncio
async def test_synthesize_no_gemini_fallback_when_cloud_disabled() -> None:
    ollama = MagicMock()
    ollama.name = "ollama"
    ollama.generate_json = AsyncMock(side_effect=ValueError("bad json"))

    router = MagicMock()
    router.get_synthesis_providers = AsyncMock(return_value=[ollama])

    with patch("presentations.llm.synthesis.LLMRouter", return_value=router) as mock_router_cls:
        with pytest.raises(ValueError, match="Failed to synthesize deck"):
            await synthesize_deck_spec(
                brief="Topic: Test",
                mode=GenerationMode.SCRATCH,
                allow_cloud=False,
                max_retries=0,
            )

    mock_router_cls.assert_called_once_with(synthesis_model_override=None, allow_cloud=False)
