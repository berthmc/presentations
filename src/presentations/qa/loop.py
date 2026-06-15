"""Bounded fix-and-verify QA loop."""

from pathlib import Path

from loguru import logger

from presentations.config.settings import get_settings
from presentations.core.schemas import DeckSpec, QAReport
from presentations.qa.render import render_slides_to_images
from presentations.qa.vlm_audit import audit_slide_images


async def run_qa_loop(
    pptx_path: str | Path,
    deck_spec: DeckSpec | None = None,
    max_iterations: int | None = None,
) -> QAReport:
    """Render and audit a deck, repeating up to max_iterations.

    Args:
        pptx_path: Generated presentation path.
        deck_spec: Optional deck spec (reserved for auto-fix iterations).
        max_iterations: Override settings max iterations.

    Returns:
        Final QAReport.
    """
    settings = get_settings()
    iterations_limit = max_iterations or settings.qa_max_iterations
    pptx = Path(pptx_path)
    report: QAReport | None = None

    for iteration in range(1, iterations_limit + 1):
        logger.info("QA iteration {}/{}", iteration, iterations_limit)
        images = await render_slides_to_images(pptx)
        report = await audit_slide_images(images)
        report.iterations = iteration
        if report.passed:
            logger.info("QA passed on iteration {}", iteration)
            break
        if deck_spec is None:
            logger.warning("QA failed and no auto-fix deck_spec provided; stopping")
            break

    assert report is not None
    return report
