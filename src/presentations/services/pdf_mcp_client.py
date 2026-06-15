"""Client for the PDF Toolbox MCP server (convert_to_markdown)."""

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from loguru import logger
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from presentations.config.settings import get_settings


def _markdown_from_tool_result(result: Any) -> str:
    """Extract markdown text from an MCP call_tool result."""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        markdown = structured.get("markdown")
        if isinstance(markdown, str):
            return markdown

    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(payload, dict):
            markdown = payload.get("markdown")
            if isinstance(markdown, str):
                return markdown
        return text

    raise ValueError("PDF MCP convert_to_markdown returned no markdown content")


async def convert_pdf_to_markdown(pdf_path: Path) -> str:
    """Copy a PDF into the MCP workspace and convert it to Markdown.

    Args:
        pdf_path: Local path to the PDF file.

    Returns:
        Markdown extracted by the PDF Toolbox MCP server.

    Raises:
        ValueError: If the MCP call fails or returns empty content.
    """
    settings = get_settings()
    workspace = settings.pdf_mcp_workspace_dir.resolve()
    ingest_dir = workspace / "pptx-briefs"
    ingest_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}.pdf"
    destination = ingest_dir / unique_name
    relative_path = f"pptx-briefs/{unique_name}"

    shutil.copy2(pdf_path, destination)
    logger.info("Staged PDF for MCP conversion: {}", relative_path)

    try:
        async with streamable_http_client(settings.pdf_mcp_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("convert_to_markdown", {"path": relative_path})
        markdown = _markdown_from_tool_result(result).strip()
        if not markdown:
            raise ValueError("PDF contains no extractable text")
        return markdown
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"PDF MCP conversion failed: {exc}") from exc
    finally:
        destination.unlink(missing_ok=True)
