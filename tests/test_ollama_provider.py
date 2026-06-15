"""Tests for Ollama provider JSON parsing and request payload."""

import json
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


@pytest.mark.asyncio
async def test_generate_json_uses_schema_and_options() -> None:
    provider = OllamaProvider(synthesis_model="qwen2.5:3b")
    schema = {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}
    response_body = {
        "message": {"content": '{"title": "Test", "slides": []}'},
        "done_reason": "stop",
        "eval_count": 12,
        "prompt_eval_count": 34,
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = response_body
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await provider.generate_json("system", "user", json_schema=schema)

    assert result["title"] == "Test"
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["format"] == schema
    assert payload["options"]["num_predict"] == provider.num_predict
    assert payload["options"]["num_ctx"] == provider.num_ctx
    assert payload["options"]["temperature"] == provider.temperature


@pytest.mark.asyncio
async def test_generate_json_recovers_braced_content() -> None:
    provider = OllamaProvider(synthesis_model="qwen2.5:3b")
    response_body = {
        "message": {"content": 'noise {"title": "Recovered", "slides": []} trailing'},
        "done_reason": "stop",
        "eval_count": 5,
        "prompt_eval_count": 10,
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = response_body
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await provider.generate_json("system", "user")

    assert result["title"] == "Recovered"
