"""Client for the hosted Context7 MCP documentation service."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from loguru import logger
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

from presentations.config.settings import Settings, get_settings

_LIBRARY_ID_PATTERN = re.compile(r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+")


def _text_from_tool_result(result: Any) -> str:
    """Extract text content from an MCP call_tool result."""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        for key in ("markdown", "content", "text", "documentation"):
            value = structured.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    content = getattr(result, "content", None) or []
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    if parts:
        return "\n".join(parts)

    raise ValueError("Context7 MCP tool returned no text content")


def _extract_library_id(text: str) -> str | None:
    """Parse a Context7 library ID from resolve-library-id output."""
    match = _LIBRARY_ID_PATTERN.search(text)
    if match:
        return match.group(0)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        for key in ("libraryId", "library_id", "id"):
            value = payload.get(key)
            if isinstance(value, str) and value.startswith("/"):
                return value
        libraries = payload.get("libraries")
        if isinstance(libraries, list) and libraries:
            first = libraries[0]
            if isinstance(first, dict):
                value = first.get("libraryId") or first.get("id")
                if isinstance(value, str):
                    return value
    return None


async def _call_context7_tool(
    settings: Settings,
    tool_name: str,
    arguments: dict[str, Any],
) -> str:
    """Call a Context7 MCP tool and return text output."""
    if not settings.context7_api_key:
        raise ValueError("CONTEXT7_API_KEY is not configured")

    headers = {"Authorization": f"Bearer {settings.context7_api_key}"}
    http_client = create_mcp_http_client(headers=headers, timeout=httpx.Timeout(60.0))

    try:
        async with streamable_http_client(settings.context7_mcp_url, http_client=http_client) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
        return _text_from_tool_result(result)
    finally:
        await http_client.aclose()


async def fetch_context7_docs(
    tech_names: list[str],
    query: str,
    *,
    settings: Settings | None = None,
) -> str:
    """Fetch documentation snippets for technologies referenced in a brief.

    Args:
        tech_names: Technology or library names to look up.
        query: Presentation brief or topic used to rank documentation relevance.
        settings: Optional settings override.

    Returns:
        Markdown sections separated by ``--- Context7: name ---`` headers.
    """
    settings = settings or get_settings()
    if not settings.context7_enabled or not settings.context7_api_key:
        return ""
    if not tech_names:
        return ""

    sections: list[str] = []
    for tech in tech_names[: settings.context7_max_techs]:
        try:
            resolve_text = await _call_context7_tool(
                settings,
                "resolve-library-id",
                {"libraryName": tech, "query": query},
            )
            library_id = _extract_library_id(resolve_text)
            if not library_id:
                logger.warning("Context7 could not resolve library id for {}", tech)
                continue

            docs = await _call_context7_tool(
                settings,
                "query-docs",
                {"libraryId": library_id, "query": query},
            )
            if docs.strip():
                sections.append(f"--- Context7: {tech} ---\n{docs.strip()}")
                logger.info("Fetched Context7 docs for {} ({})", tech, library_id)
        except Exception as exc:
            logger.warning("Context7 lookup failed for {}: {}", tech, exc)

    return "\n\n".join(sections)
