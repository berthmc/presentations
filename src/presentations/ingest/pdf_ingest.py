"""Extract source context from PDF documents for synthesis grounding."""

from pathlib import Path

from loguru import logger

from presentations.services.pdf_mcp_client import convert_pdf_to_markdown

_MAX_SOURCE_CONTEXT_CHARS = 100_000


async def extract_source_context_from_pdf(pdf_path: Path) -> str:
    """Convert a PDF file to Markdown for use as synthesis grounding context.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        Markdown text extracted from the PDF via the PDF Toolbox MCP server.

    Raises:
        ValueError: If the file is missing, not a PDF, or yields no text.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise ValueError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    logger.info("Extracting source context from PDF via MCP: {}", path.name)
    text = await convert_pdf_to_markdown(path)

    if len(text) > _MAX_SOURCE_CONTEXT_CHARS:
        logger.warning(
            "PDF source context truncated from {} to {} characters",
            len(text),
            _MAX_SOURCE_CONTEXT_CHARS,
        )
        text = text[:_MAX_SOURCE_CONTEXT_CHARS]

    return text
