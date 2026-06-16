"""Five-stage pipeline orchestrator with validation rollback loop."""

from loguru import logger

from presentations.agents.assembler import run_assembler
from presentations.agents.inspector import run_inspector
from presentations.agents.planner import run_planner
from presentations.agents.profiler import run_profiler
from presentations.agents.researcher import run_researcher
from presentations.config.settings import get_settings
from presentations.core.schemas import GenerateRequest, GenerateResult, GenerationMode, LayoutProfile
from presentations.core.state import PipelineStage, PipelineState
from presentations.ingest.theme_md3 import load_md3_theme
from presentations.services.generation_context import resolve_generation_context


async def generate_presentation(request: GenerateRequest) -> GenerateResult:
    """Run the five-stage agent pipeline with optional QA rollback to Planner.

    Stages:
        1. Researcher — RAG + Context7
        2. Profiler — layout manifest
        3. Planner — DeckSpec JSON
        4. Assembler — native .pptx
        5. Inspector — validation loop with rollback to stage 3

    Args:
        request: Generation parameters.

    Returns:
        GenerateResult with output path and QA report.
    """
    settings = get_settings()
    template_path, layout_profile, mode = resolve_generation_context(request)
    if mode == GenerationMode.TEMPLATE and not template_path:
        raise ValueError("template_id or template_path required for template mode")

    state = PipelineState(
        request=request,
        layout_profile=layout_profile,
        template_path=template_path,
        mode=mode.value,
        max_revisions=settings.max_revisions,
    )

    state = await run_researcher(state)
    state.stage = PipelineStage.PROFILE
    state = await run_profiler(state)

    while state.revision <= state.max_revisions:
        state.stage = PipelineStage.PLAN
        state = await run_planner(state)

        state.stage = PipelineStage.ASSEMBLE
        state = await run_assembler(state)

        if not request.run_qa:
            break

        state.stage = PipelineStage.INSPECT
        state = await run_inspector(state)

        if state.qa_report and state.qa_report.passed:
            logger.info("Inspector passed on revision {}", state.revision)
            break

        if state.revision >= state.max_revisions:
            logger.warning("Inspector failed after {} revisions; returning last output", state.revision)
            break

        logger.info(
            "Inspector failed revision {}; rolling back to Planner with {} reasons",
            state.revision,
            len(state.rollback_reasons),
        )
        state.revision += 1

    if layout_profile is None and mode == GenerationMode.SCRATCH:
        layout_profile = LayoutProfile(
            source_path="scratch",
            source_type="md3",
            layouts={},
            theme=load_md3_theme("tech"),
        )

    assert state.deck_spec is not None
    assert state.output_path is not None

    return GenerateResult(
        output_path=state.output_path,
        deck_spec=state.deck_spec,
        qa_report=state.qa_report,
        layout_profile=layout_profile,
    )
