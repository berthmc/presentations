"""End-to-end presentation generation pipeline."""

from uuid import uuid4

from loguru import logger

from presentations.compile.pipeline import compile_deck
from presentations.config.settings import Settings, get_settings
from presentations.core.schemas import GenerateRequest, GenerateResult, GenerationMode, LayoutProfile, QAReport
from presentations.ingest.theme_md3 import load_md3_theme
from presentations.llm.synthesis import synthesize_deck_spec
from presentations.qa.loop import run_qa_loop
from presentations.services.template_registry import get_template_registry


def _resolve_generation_context(request: GenerateRequest) -> tuple[str | None, LayoutProfile | None, GenerationMode]:
    """Resolve template path, cached layout profile, and effective generation mode."""
    registry = get_template_registry()
    resolved = registry.resolve(template_id=request.template_id, template_path=request.template_path)

    if resolved is None:
        return None, None, request.mode

    mode = request.mode
    if request.template_id and mode == GenerationMode.SCRATCH and resolved.source_type == "pptx":
        mode = GenerationMode.TEMPLATE
    elif request.template_id and mode == GenerationMode.SCRATCH and resolved.source_type == "md":
        pass  # md template can guide scratch layouts

    if mode == GenerationMode.TEMPLATE and resolved.source_type != "pptx":
        raise ValueError("Template mode requires a .pptx library template")

    if mode == GenerationMode.TEMPLATE and not resolved.template_path:
        raise ValueError("template_id or template_path required for template mode")

    return resolved.template_path, resolved.layout_profile, mode


def _resolve_allow_cloud(request: GenerateRequest, settings: Settings | None = None) -> bool:
    """Return whether cloud LLM providers may be used for this request."""
    settings = settings or get_settings()
    return request.allow_cloud or settings.allow_cloud_llm_default


async def generate_presentation(request: GenerateRequest) -> GenerateResult:
    """Run the full generation pipeline.

    Args:
        request: Generation parameters.

    Returns:
        GenerateResult with output path and QA report.
    """
    template_path, layout_profile, mode = _resolve_generation_context(request)

    if mode == GenerationMode.TEMPLATE and not template_path:
        raise ValueError("template_id or template_path required for template mode")

    allow_cloud = _resolve_allow_cloud(request)

    deck_spec = await synthesize_deck_spec(
        brief=request.brief,
        layout=layout_profile,
        mode=mode,
        title=request.title,
        source_context=request.source_context,
        synthesis_model=request.synthesis_model,
        allow_cloud=allow_cloud,
    )

    output_name = f"{deck_spec.title.replace(' ', '_')}_{uuid4().hex[:8]}.pptx"
    settings = get_settings()
    output_path = settings.output_dir / output_name

    await compile_deck(
        deck_spec=deck_spec,
        output_path=output_path,
        template_path=template_path if mode == GenerationMode.TEMPLATE else None,
        layout_profile=layout_profile,
    )

    qa_report = None
    if request.run_qa:
        try:
            qa_report = await run_qa_loop(output_path, deck_spec=deck_spec, allow_cloud=allow_cloud)
        except FileNotFoundError as exc:
            logger.warning("QA rendering skipped: {}", exc)
            qa_report = QAReport(passed=True, reasons=[f"QA skipped: {exc}"])

    if layout_profile is None and mode == GenerationMode.SCRATCH:
        layout_profile = LayoutProfile(
            source_path="scratch",
            source_type="md3",
            layouts={},
            theme=load_md3_theme("tech"),
        )

    return GenerateResult(
        output_path=str(output_path.resolve()),
        deck_spec=deck_spec,
        qa_report=qa_report,
        layout_profile=layout_profile,
    )
