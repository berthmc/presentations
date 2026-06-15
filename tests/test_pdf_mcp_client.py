"""Tests for PDF Toolbox MCP client helpers."""

import json
from types import SimpleNamespace

import pytest

from presentations.services.pdf_mcp_client import _markdown_from_tool_result


def test_markdown_from_tool_result_structured_content() -> None:
    result = SimpleNamespace(structuredContent={"markdown": "# Title\n\nBody"}, content=[])
    assert _markdown_from_tool_result(result) == "# Title\n\nBody"


def test_markdown_from_tool_result_json_text() -> None:
    payload = json.dumps({"markdown": "Hello from JSON"})
    result = SimpleNamespace(structuredContent=None, content=[SimpleNamespace(text=payload)])
    assert _markdown_from_tool_result(result) == "Hello from JSON"


def test_markdown_from_tool_result_plain_text() -> None:
    result = SimpleNamespace(structuredContent=None, content=[SimpleNamespace(text="Plain markdown")])
    assert _markdown_from_tool_result(result) == "Plain markdown"


def test_markdown_from_tool_result_raises_when_empty() -> None:
    result = SimpleNamespace(structuredContent=None, content=[])
    with pytest.raises(ValueError, match="no markdown content"):
        _markdown_from_tool_result(result)
