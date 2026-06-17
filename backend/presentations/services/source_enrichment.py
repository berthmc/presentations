"""Enrich generation requests with optional Context7 documentation."""

from __future__ import annotations

from loguru import logger

from presentations.config.settings import Settings, get_settings
from presentations.services.context7_client import fetch_context7_docs
from presentations.services.topic_classifier import extract_technologies, is_it_topic


async def enrich_source_context(
    brief: str,
    source_context: str | None,
    *,
    settings: Settings | None = None,
) -> str | None:
    """Append Context7 documentation to source context for IT-topic briefs."""
    settings = settings or get_settings()
    if not settings.context7_enabled or not settings.context7_api_key:
        return source_context
    if not is_it_topic(brief):
        return source_context

    tech_names = extract_technologies(brief, max_items=settings.context7_max_techs)
    if not tech_names:
        logger.info("IT topic detected but no technologies extracted from brief")
        return source_context

    logger.info("Fetching Context7 docs for technologies: {}", tech_names)
    context7_docs = await fetch_context7_docs(tech_names, query=brief, settings=settings)
    if not context7_docs.strip():
        return source_context

    if source_context:
        return f"{source_context.strip()}\n\n{context7_docs.strip()}"
    return context7_docs.strip()
