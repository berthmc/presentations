"""Tests for Context7 MCP client helpers."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from presentations.services.context7_client import _extract_library_id, fetch_context7_docs


def test_extract_library_id_from_markdown_text() -> None:
    text = "Selected library ID: /websites/webrtc\nReason: exact match"
    assert _extract_library_id(text) == "/websites/webrtc"


def test_extract_library_id_from_json_payload() -> None:
    payload = json.dumps({"libraryId": "/openai/whisper"})
    assert _extract_library_id(payload) == "/openai/whisper"


@pytest.mark.asyncio
async def test_fetch_context7_docs_returns_empty_when_disabled() -> None:
    from presentations.config.settings import Settings

    settings = Settings(
        _env_file=None,
        CONTEXT7_ENABLED=False,
        CONTEXT7_API_KEY="ctx7sk-test",
    )
    result = await fetch_context7_docs(["WebRTC"], "speech architecture", settings=settings)
    assert result == ""


@pytest.mark.asyncio
async def test_fetch_context7_docs_merges_sections() -> None:
    from presentations.config.settings import Settings

    settings = Settings(
        _env_file=None,
        CONTEXT7_ENABLED=True,
        CONTEXT7_API_KEY="ctx7sk-test",
        CONTEXT7_MAX_TECHS=1,
    )

    with patch(
        "presentations.services.context7_client._call_context7_tool",
        new=AsyncMock(
            side_effect=[
                "Library ID: /websites/webrtc",
                "WebRTC peer connection setup examples.",
            ]
        ),
    ):
        result = await fetch_context7_docs(["WebRTC"], "speech architecture", settings=settings)

    assert "--- Context7: WebRTC ---" in result
    assert "peer connection" in result
