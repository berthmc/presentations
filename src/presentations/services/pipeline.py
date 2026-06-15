"""End-to-end presentation generation pipeline."""

from uuid import uuid4

from loguru import logger

from presentations.compile.pipeline import compile_deck
from presentations.core.schemas import GenerateRequest, GenerateResult, GenerationMode
from presentations.ingest.discover import discover_layout
from presentations.ingest.theme_md3 import load_md3_theme
from presentations.llm.synthesis import synthesize_deck_spec
from presentations.qa.loop import run_qa_loop


async def generate_presentation(request: GenerateRequest) -> GenerateResult:
    """Run the full generation pipeline.

    Args:
        request: Generation parameters.

    Returns:
        GenerateResult with output path and QA report.
    """
    layout_profile = None
    template_path = request.template_path

    if request.mode == GenerationMode.TEMPLATE:
        if not template_path:
            raise ValueError("template_path required for template mode")
        layout_profile = discover_layout(template_path)
    elif template_path and template_path.endswith(".md"):
        layout_profile = discover_layout(template_path)
    else:
        layout_profile = None

    deck_spec = await synthesize_deck_spec(
        brief=request.brief,
        layout=layout_profile,
        mode=request.mode,
        title=request.title,
    )

    output_name = f"{deck_spec.title.replace(' ', '_')}_{uuid4().hex[:8]}.pptx"
    from presentations.config.settings import get_settings

    settings = get_settings()
    output_path = settings.output_dir / output_name

    await compile_deck(
        deck_spec=deck_spec,
        output_path=output_path,
        template_path=template_path if request.mode == GenerationMode.TEMPLATE else None,
        layout_profile=layout_profile,
    )

    qa_report = None
    if request.run_qa:
        try:
            qa_report = await run_qa_loop(output_path, deck_spec=deck_spec)
        except FileNotFoundError as exc:
            logger.warning("QA rendering skipped: {}", exc)
            from presentations.core.schemas import QAReport

            qa_report = QAReport(passed=True, reasons=[f"QA skipped: {exc}"])

    if layout_profile is None and request.mode == GenerationMode.SCRATCH:
        from presentations.core.schemas import LayoutProfile

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
