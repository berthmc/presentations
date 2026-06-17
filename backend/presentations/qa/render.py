"""Render presentations to slide images for QA."""

import asyncio
import shutil
import subprocess
from pathlib import Path

from loguru import logger

from presentations.config.settings import get_settings


def _find_soffice() -> str:
    """Locate LibreOffice soffice binary."""
    for candidate in ("soffice", "libreoffice"):
        path = shutil.which(candidate)
        if path:
            return path
    raise FileNotFoundError("LibreOffice (soffice) not found. Install libreoffice-impress.")


def _find_pdftoppm() -> str:
    """Locate pdftoppm binary."""
    path = shutil.which("pdftoppm")
    if not path:
        raise FileNotFoundError("pdftoppm not found. Install poppler-utils.")
    return path


async def render_slides_to_images(pptx_path: str | Path, output_dir: str | Path | None = None) -> list[Path]:
    """Convert a .pptx deck to JPEG slide images via PDF intermediate.

    Args:
        pptx_path: Source presentation.
        output_dir: Directory for slide images (defaults to settings qa_dir).

    Returns:
        Ordered list of slide image paths.
    """
    settings = get_settings()
    pptx = Path(pptx_path).resolve()
    staging = settings.staging_dir
    staging.mkdir(parents=True, exist_ok=True)
    out_dir = Path(output_dir) if output_dir else settings.qa_dir / pptx.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    soffice = _find_soffice()
    pdftoppm = _find_pdftoppm()
    pdf_path = staging / f"{pptx.stem}.pdf"
    prefix = out_dir / "slide"

    logger.info("Rendering {} to PDF via LibreOffice", pptx.name)
    await asyncio.to_thread(
        subprocess.run,
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(staging), str(pptx)],
        check=True,
        capture_output=True,
    )
    if not pdf_path.exists():
        pdfs = list(staging.glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError(f"PDF not produced for {pptx}")
        pdf_path = pdfs[-1]

    logger.info("Rasterizing PDF to JPEG at {} DPI", settings.qa_render_dpi)
    await asyncio.to_thread(
        subprocess.run,
        [pdftoppm, "-jpeg", "-r", str(settings.qa_render_dpi), str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
    )

    images = sorted(out_dir.glob("slide-*.jpg"))
    if not images:
        images = sorted(out_dir.glob("slide*.jpg"))
    logger.info("Rendered {} slide images", len(images))
    return images
