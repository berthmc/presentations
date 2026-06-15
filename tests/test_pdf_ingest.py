"""Tests for PDF brief ingestion."""

from pathlib import Path
from unittest.mock import patch

import pytest

from presentations.ingest.pdf_ingest import extract_brief_from_pdf


def test_extract_brief_from_pdf_returns_markdown(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("presentations.ingest.pdf_ingest.pymupdf4llm.to_markdown", return_value="# Title\n\nBody text"):
        result = extract_brief_from_pdf(pdf_path)

    assert result == "# Title\n\nBody text"


def test_extract_brief_from_pdf_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="PDF not found"):
        extract_brief_from_pdf(tmp_path / "missing.pdf")


def test_extract_brief_from_pdf_rejects_empty_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("presentations.ingest.pdf_ingest.pymupdf4llm.to_markdown", return_value="   "):
        with pytest.raises(ValueError, match="no extractable text"):
            extract_brief_from_pdf(pdf_path)


def test_extract_brief_from_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    doc_path = tmp_path / "notes.txt"
    doc_path.write_text("not a pdf")

    with pytest.raises(ValueError, match="Expected a .pdf file"):
        extract_brief_from_pdf(doc_path)
