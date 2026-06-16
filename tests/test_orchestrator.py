"""Tests for five-stage orchestrator rollback behaviour."""

from unittest.mock import AsyncMock, patch

import pytest

from presentations.agents.orchestrator import generate_presentation
from presentations.core.schemas import (
    DeckSpec,
    GenerateRequest,
    GenerationMode,
    PlaceholderMapping,
    QAReport,
    SlideSpec,
)


@pytest.mark.asyncio
async def test_orchestrator_rolls_back_to_planner_on_qa_failure() -> None:
    request = GenerateRequest(brief="Rollback test", mode=GenerationMode.SCRATCH, run_qa=True)
    deck = DeckSpec(
        title="Rollback Deck",
        mode=GenerationMode.SCRATCH,
        slides=[SlideSpec(layout_index=0, mappings=[PlaceholderMapping(ph_idx=0, content="Title")])],
    )
    planner_calls = 0

    async def fake_planner(state):
        nonlocal planner_calls
        planner_calls += 1
        state.deck_spec = deck
        return state

    async def fake_assembler(state):
        state.output_path = "C:/tmp/test_deck.pptx"
        return state

    async def fake_inspector(state):
        state.qa_report = QAReport(
            passed=planner_calls > 1,
            reasons=[] if planner_calls > 1 else ["overflow"],
            iterations=planner_calls,
        )
        if not state.qa_report.passed:
            state.rollback_reasons = ["Slide 1 title overflows; shorten"]
        return state

    with (
        patch("presentations.agents.orchestrator.run_researcher", new=AsyncMock(side_effect=lambda s: s)),
        patch("presentations.agents.orchestrator.run_profiler", new=AsyncMock(side_effect=lambda s: s)),
        patch("presentations.agents.orchestrator.run_planner", new=fake_planner),
        patch("presentations.agents.orchestrator.run_assembler", new=fake_assembler),
        patch("presentations.agents.orchestrator.run_inspector", new=fake_inspector),
        patch(
            "presentations.agents.orchestrator.resolve_generation_context",
            return_value=(None, None, GenerationMode.SCRATCH),
        ),
        patch("presentations.config.settings.get_settings") as mock_settings,
    ):
        mock_settings.return_value.max_revisions = 2
        result = await generate_presentation(request)

    assert planner_calls == 2
    assert result.qa_report is not None
    assert result.qa_report.passed is True
