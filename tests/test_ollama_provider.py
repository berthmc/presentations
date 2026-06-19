"""Tests for Ollama provider JSON parsing and request payload."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from presentations.llm.ollama_provider import OllamaProvider, parse_json_content


def test_parse_json_content_plain() -> None:
    assert parse_json_content('{"title": "Deck", "slides": []}') == {"title": "Deck", "slides": []}


def test_parse_json_content_with_surrounding_text() -> None:
    raw = 'Here is JSON:\n{"title": "Deck", "slides": [{"layout_index": 0, "mappings": []}]}\nDone.'
    result = parse_json_content(raw)
    assert result["title"] == "Deck"
    assert len(result["slides"]) == 1


def test_parse_json_content_invalid_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_json_content("{")


def _stream_lines(*lines: str):
    captured: dict[str, object] = {}

    @asynccontextmanager
    async def mock_stream(*_args, **kwargs):
        captured["json"] = kwargs.get("json")
        response = MagicMock()
        response.raise_for_status = MagicMock()

        async def aiter_lines():
            for line in lines:
                yield line

        response.aiter_lines = aiter_lines
        yield response

    mock_stream.captured = captured
    return mock_stream


@pytest.mark.asyncio
async def test_generate_json_uses_schema_and_streaming() -> None:
    provider = OllamaProvider(synthesis_model="qwen2.5:3b")
    schema = {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}
    stream_line = json.dumps(
        {
            "message": {"content": '{"title": "Test", "slides": []}'},
            "done": True,
            "done_reason": "stop",
            "eval_count": 12,
            "prompt_eval_count": 34,
        }
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_stream = _stream_lines(stream_line)
        mock_client = AsyncMock()
        mock_client.stream = mock_stream
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await provider.generate_json("system", "user", json_schema=schema)

    assert result["title"] == "Test"
    payload = mock_stream.captured["json"]
    assert payload["stream"] is True
    assert payload["format"] == schema
    assert payload["options"]["num_predict"] == provider.num_predict
    assert payload["options"]["num_ctx"] == provider.num_ctx
    assert payload["options"]["temperature"] == provider.temperature


@pytest.mark.asyncio
async def test_generate_json_recovers_braced_content_from_stream() -> None:
    provider = OllamaProvider(synthesis_model="qwen2.5:3b")
    stream_line = json.dumps(
        {
            "message": {"content": 'noise {"title": "Recovered", "slides": []} trailing'},
            "done": True,
            "done_reason": "stop",
            "eval_count": 5,
            "prompt_eval_count": 10,
        }
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.stream = _stream_lines(stream_line)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await provider.generate_json("system", "user")

    assert result["title"] == "Recovered"


@pytest.mark.asyncio
async def test_generate_json_accumulates_multiple_stream_chunks() -> None:
    provider = OllamaProvider(synthesis_model="qwen2.5:3b")
    first = json.dumps({"message": {"content": '{"title": "Chunked"'}, "done": False})
    second = json.dumps(
        {
            "message": {"content": ', "slides": []}'},
            "done": True,
            "eval_count": 3,
            "prompt_eval_count": 8,
        }
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.stream = _stream_lines(first, second)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await provider.generate_json("system", "user")

    assert result == {"title": "Chunked", "slides": []}
