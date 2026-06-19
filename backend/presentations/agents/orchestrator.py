"""Five-stage pipeline orchestrator with validation rollback loop."""

import time

from loguru import logger

from presentations.agents.assembler import run_assembler
from presentations.agents.inspector import run_inspector
from presentations.agents.planner import run_planner
from presentations.agents.profiler import run_profiler
from presentations.agents.researcher import run_researcher
from presentations.config.pipeline_logging import pipeline_stage, resolve_run_id, summarize_deck_spec
from presentations.config.settings import get_settings
from presentations.core.schemas import GenerateRequest, GenerateResult, GenerationMode, LayoutProfile
from presentations.core.state import PipelineStage, PipelineState
from presentations.ingest.theme_md3 import load_md3_theme
from presentations.services.generation_context import resolve_generation_context
from presentations.services.job_store import JobStatus, get_job_store


async def _report_stage(job_id: str | None, stage: PipelineStage) -> None:
    """Update job store with the current pipeline stage when tracking a job."""
    if job_id is None:
        return
    await get_job_store().update(job_id, status=JobStatus.RUNNING, stage=stage)


async def generate_presentation(request: GenerateRequest, *, job_id: str | None = None) -> GenerateResult:
    """Run the five-stage agent pipeline with optional QA rollback to Planner.

    Stages:
        1. Researcher — RAG + Context7
        2. Profiler — layout manifest
        3. Planner — DeckSpec JSON
        4. Assembler — native .pptx
        5. Inspector — validation loop with rollback to stage 3

    Args:
        request: Generation parameters.
        job_id: Optional async job identifier for stage progress updates.

    Returns:
        GenerateResult with output path and QA report.
    """
    settings = get_settings()
    run_id = resolve_run_id(job_id)
    pipeline_started = time.perf_counter()
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

    with logger.contextualize(run_id=run_id, stage="-", revision="0"):
        logger.info(
            "Pipeline started mode={} run_qa={} allow_cloud={} synthesis_model={} brief_chars={} source_chars={} max_revisions={}",
            mode.value,
            request.run_qa,
            request.allow_cloud,
            request.synthesis_model or "default",
            len(request.brief),
            len(request.source_context or ""),
            settings.max_revisions,
        )

    async with pipeline_stage(run_id, PipelineStage.RESEARCH, revision=0) as metrics:
        await _report_stage(job_id, PipelineStage.RESEARCH)
        state = await run_researcher(state)
        metrics["snippets"] = len(state.research.snippets)

    state.stage = PipelineStage.PROFILE
    async with pipeline_stage(run_id, PipelineStage.PROFILE, revision=0) as metrics:
        await _report_stage(job_id, PipelineStage.PROFILE)
        state = await run_profiler(state)
        if state.layout_profile and state.layout_profile.layouts:
            metrics["layouts"] = len(state.layout_profile.layouts)
            metrics["placeholders"] = sum(
                len(entry.placeholders) for entry in state.layout_profile.layouts.values()
            )

    while state.revision <= state.max_revisions:
        if state.revision > 0:
            with logger.contextualize(run_id=run_id, stage="-", revision=str(state.revision)):
                logger.info("Revision loop revision={}/{}", state.revision, state.max_revisions)

        state.stage = PipelineStage.PLAN
        async with pipeline_stage(run_id, PipelineStage.PLAN, revision=state.revision) as metrics:
            await _report_stage(job_id, PipelineStage.PLAN)
            state = await run_planner(state)
            if state.deck_spec:
                deck_summary = summarize_deck_spec(state.deck_spec)
                metrics.update({k: deck_summary[k] for k in ("slides", "mappings")})

        state.stage = PipelineStage.ASSEMBLE
        async with pipeline_stage(run_id, PipelineStage.ASSEMBLE, revision=state.revision) as metrics:
            await _report_stage(job_id, PipelineStage.ASSEMBLE)
            state = await run_assembler(state)
            if state.output_path:
                metrics["output"] = state.output_path

        if not request.run_qa:
            break

        state.stage = PipelineStage.INSPECT
        async with pipeline_stage(run_id, PipelineStage.INSPECT, revision=state.revision) as metrics:
            await _report_stage(job_id, PipelineStage.INSPECT)
            state = await run_inspector(state)
            if state.qa_report:
                metrics["passed"] = state.qa_report.passed
                metrics["errors"] = sum(1 for issue in state.qa_report.issues if issue.severity == "error")
                metrics["warnings"] = sum(1 for issue in state.qa_report.issues if issue.severity == "warning")

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

    if state.deck_spec is None or state.output_path is None:
        raise RuntimeError("Pipeline finished without producing a deck spec and output path")

    qa_passed = state.qa_report.passed if state.qa_report else None
    total_duration = time.perf_counter() - pipeline_started
    with logger.contextualize(run_id=run_id, stage="-", revision=str(state.revision)):
        logger.info(
            "Pipeline complete output={} slides={} qa_passed={} revisions={} duration_s={:.2f}",
            state.output_path,
            len(state.deck_spec.slides),
            qa_passed,
            state.revision + 1,
            total_duration,
        )

    return GenerateResult(
        output_path=state.output_path,
        deck_spec=state.deck_spec,
        qa_report=state.qa_report,
        layout_profile=layout_profile,
    )
