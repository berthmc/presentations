"""Tests for PDF source context ingestion."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from presentations.ingest.pdf_ingest import extract_source_context_from_pdf


@pytest.mark.asyncio
async def test_extract_source_context_from_pdf_returns_markdown(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch(
        "presentations.ingest.pdf_ingest.parse_pdf_to_markdown",
        new=AsyncMock(return_value="# Title\n\nBody text"),
    ):
        result = await extract_source_context_from_pdf(pdf_path)

    assert result == "# Title\n\nBody text"


@pytest.mark.asyncio
async def test_extract_source_context_from_pdf_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="PDF not found"):
        await extract_source_context_from_pdf(tmp_path / "missing.pdf")


@pytest.mark.asyncio
async def test_extract_source_context_from_pdf_rejects_empty_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch(
        "presentations.ingest.pdf_ingest.parse_pdf_to_markdown",
        new=AsyncMock(side_effect=ValueError("PDF contains no extractable text")),
    ):
        with pytest.raises(ValueError, match="no extractable text"):
            await extract_source_context_from_pdf(pdf_path)


@pytest.mark.asyncio
async def test_extract_source_context_from_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    doc_path = tmp_path / "notes.txt"
    doc_path.write_text("not a pdf")

    with pytest.raises(ValueError, match="Expected a .pdf file"):
        await extract_source_context_from_pdf(doc_path)
