"""Stage 3: Content mapping and deck specification synthesis (Planner)."""

from loguru import logger

from presentations.config.pipeline_logging import summarize_deck_spec
from presentations.core.schemas import GenerationMode
from presentations.core.state import PipelineState
from presentations.llm.synthesis import synthesize_deck_spec


async def run_planner(state: PipelineState) -> PipelineState:
    """Cross-reference research snippets against layout manifest and produce DeckSpec.

    Args:
        state: Pipeline state with research and layout_profile.

    Returns:
        Updated state with deck_spec.
    """
    request = state.request
    mode = GenerationMode(state.mode or request.mode.value)
    source_context = state.research.to_prompt_text() or request.source_context

    if state.rollback_reasons:
        feedback = "\n".join(f"- {reason}" for reason in state.rollback_reasons)
        logger.info(
            "Planner applying {} rollback reason(s) on revision {}",
            len(state.rollback_reasons),
            state.revision,
        )
        source_context = (
            f"{source_context or ''}\n\n"
            f"QA rollback feedback (fix these issues):\n{feedback}"
        ).strip()

    deck_spec = await synthesize_deck_spec(
        brief=request.brief,
        layout=state.layout_profile,
        mode=mode,
        title=request.title,
        source_context=source_context,
        digest_source_context=request.source_context,
        synthesis_model=request.synthesis_model,
        allow_cloud=request.allow_cloud,
    )
    state.deck_spec = deck_spec
    summary = summarize_deck_spec(deck_spec)
    logger.info(
        "Planner produced deck title={} slides={} layouts={} mappings={} (revision {})",
        summary["title"],
        summary["slides"],
        summary["layouts"],
        summary["mappings"],
        state.revision,
    )
    return state
