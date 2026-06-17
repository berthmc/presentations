"""Tests for pipeline stage logging helpers and orchestrator log markers."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from loguru import logger
from presentations.agents.orchestrator import generate_presentation
from presentations.config.pipeline_logging import (
    resolve_run_id,
    stage_marker,
    summarize_deck_spec,
    summarize_pptx_file,
)
from presentations.core.schemas import (
    DeckSpec,
    GenerateRequest,
    GenerationMode,
    PlaceholderMapping,
    SlideSpec,
)


def test_resolve_run_id_uses_job_prefix() -> None:
    job_id = "abcdef12-3456-7890-abcd-ef1234567890"
    assert resolve_run_id(job_id) == "abcdef12"


def test_resolve_run_id_generates_short_id_when_missing() -> None:
    run_id = resolve_run_id(None)
    assert len(run_id) == 8


def test_stage_marker_format() -> None:
    from presentations.core.state import PipelineStage

    assert stage_marker(PipelineStage.RESEARCH) == "1/5 research"
    assert stage_marker(PipelineStage.ASSEMBLE) == "4/5 assemble"


def test_summarize_deck_spec() -> None:
    deck = DeckSpec(
        title="Test Deck",
        mode=GenerationMode.SCRATCH,
        slides=[
            SlideSpec(
                layout_index=0,
                mappings=[
                    PlaceholderMapping(ph_idx=0, content="Title"),
                    PlaceholderMapping(ph_idx=1, content="Body"),
                ],
            ),
            SlideSpec(layout_index=1, mappings=[PlaceholderMapping(ph_idx=0, content="Slide 2")]),
        ],
    )
    summary = summarize_deck_spec(deck)
    assert summary["title"] == "Test Deck"
    assert summary["slides"] == 2
    assert summary["mappings"] == 3
    assert summary["content_chars"] == len("Title") + len("Body") + len("Slide 2")
    assert summary["layouts"] == {0: 1, 1: 1}


def test_summarize_pptx_file(tmp_path: Path) -> None:
    pptx_path = tmp_path / "deck.pptx"
    pptx_path.write_bytes(b"x" * 2048)
    summary = summarize_pptx_file(pptx_path)
    assert summary["exists"] is True
    assert summary["size_kb"] == 2.0

    missing = summarize_pptx_file(tmp_path / "missing.pptx")
    assert missing["exists"] is False


@pytest.mark.asyncio
async def test_orchestrator_emits_stage_markers(tmp_path: Path) -> None:
    request = GenerateRequest(brief="Logging test", mode=GenerationMode.SCRATCH, run_qa=False)
    deck = DeckSpec(
        title="Log Deck",
        mode=GenerationMode.SCRATCH,
        slides=[SlideSpec(layout_index=0, mappings=[PlaceholderMapping(ph_idx=0, content="Title")])],
    )
    output_path = tmp_path / "log_deck.pptx"
    output_path.write_bytes(b"fake-pptx")

    log_messages: list[str] = []

    def _sink(message) -> None:
        log_messages.append(message.record["message"])

    sink_id = logger.add(_sink, format="{message}")

    async def fake_assembler(state):
        state.output_path = str(output_path)
        return state

    async def fake_planner(state):
        state.deck_spec = deck
        return state

    try:
        with (
            patch("presentations.agents.orchestrator.run_researcher", new=AsyncMock(side_effect=lambda s: s)),
            patch("presentations.agents.orchestrator.run_profiler", new=AsyncMock(side_effect=lambda s: s)),
            patch("presentations.agents.orchestrator.run_planner", new=fake_planner),
            patch("presentations.agents.orchestrator.run_assembler", new=fake_assembler),
            patch(
                "presentations.agents.orchestrator.resolve_generation_context",
                return_value=(None, None, GenerationMode.SCRATCH),
            ),
            patch("presentations.config.settings.get_settings") as mock_settings,
        ):
            mock_settings.return_value.max_revisions = 2
            job_id = "testjob1-0000-0000-0000-000000000001"
            await generate_presentation(request, job_id=job_id)

        joined = "\n".join(log_messages)
        assert "Pipeline started" in joined
        assert "Pipeline stage 1/5 research started" in joined
        assert "Pipeline stage 2/5 profile started" in joined
        assert "Pipeline stage 3/5 plan started" in joined
        assert "Pipeline stage 4/5 assemble started" in joined
        assert "Pipeline complete" in joined
    finally:
        logger.remove(sink_id)
