"""Parse PDFs to Markdown using Docling (optional) with MCP fallback."""

from pathlib import Path

from loguru import logger

from presentations.config.settings import get_settings


async def parse_pdf_to_markdown(pdf_path: Path) -> str:
    """Convert a PDF to Markdown using Docling when available.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Markdown text extracted from the document.

    Raises:
        ValueError: When the file is missing or not a PDF.
        ImportError: When Docling is not installed and MCP fallback is disabled.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise ValueError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    settings = get_settings()
    if settings.use_docling:
        try:
            return _parse_with_docling(path)
        except ImportError:
            logger.warning("Docling not installed; falling back to PDF MCP")
        except Exception as exc:
            logger.warning("Docling parse failed ({}); falling back to PDF MCP", exc)

    from presentations.services.pdf_mcp_client import convert_pdf_to_markdown

    return await convert_pdf_to_markdown(path)


def _parse_with_docling(pdf_path: Path) -> str:
    """Parse PDF via Docling document converter."""
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    return result.document.export_to_markdown()
