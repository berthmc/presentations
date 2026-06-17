"""Stage 1: Document ingestion, RAG retrieval, and Context7 enrichment."""

from collections import Counter

from loguru import logger

from presentations.config.settings import get_settings
from presentations.core.state import PipelineState, ResearchPayload, ResearchSnippet
from presentations.rag.indexer import index_document
from presentations.rag.retriever import retrieve_research_snippets
from presentations.services.context7_client import fetch_context7_docs
from presentations.services.topic_classifier import extract_technologies, is_it_topic


async def run_researcher(state: PipelineState) -> PipelineState:
    """Index source material, retrieve snippets, and enrich with Context7 docs.

    Args:
        state: Current pipeline state with request populated.

    Returns:
        Updated state with research payload.
    """
    settings = get_settings()
    request = state.request
    snippets: list[ResearchSnippet] = []

    if request.source_context and settings.rag_enabled:
        doc_id = "uploaded_source"
        indexed = await index_document(doc_id, request.source_context, settings=settings)
        logger.info("RAG indexed {} chunks for uploaded source", indexed)
        retrieved = await retrieve_research_snippets(request.brief, doc_id=doc_id, settings=settings)
        snippets.extend(retrieved.snippets)
        logger.info("RAG retrieved {} snippets for brief", len(retrieved.snippets))
    elif request.source_context:
        logger.info("RAG disabled; will use raw source fallback if no snippets retrieved")

    if not snippets and request.source_context:
        logger.info("Using raw source fallback ({} chars)", len(request.source_context))
        snippets.append(
            ResearchSnippet(
                claim=request.source_context[:500],
                source_quote=request.source_context,
                doc_id="raw_source",
                score=1.0,
            )
        )

    if settings.context7_enabled and settings.context7_api_key and is_it_topic(request.brief):
        tech_names = extract_technologies(request.brief, max_items=settings.context7_max_techs)
        if tech_names:
            logger.info("Context7 fetching docs for technologies: {}", tech_names)
            context7_docs = await fetch_context7_docs(tech_names, query=request.brief, settings=settings)
            if context7_docs.strip():
                snippets.append(
                    ResearchSnippet(
                        claim=context7_docs[:500],
                        source_quote=context7_docs,
                        doc_id="context7",
                        score=0.9,
                        metadata={"technologies": tech_names},
                    )
                )
                logger.info("Context7 added snippet ({} chars)", len(context7_docs))
            else:
                logger.info("Context7 returned no documentation for {}", tech_names)
        else:
            logger.info("IT topic detected but no technologies extracted from brief")
    elif is_it_topic(request.brief):
        logger.info("Context7 skipped (disabled or missing API key)")

    state.research = ResearchPayload(snippets=snippets)
    state.stage = state.stage  # caller sets stage transitions
    by_doc = dict(Counter(snippet.doc_id or "unknown" for snippet in snippets))
    logger.info("Researcher produced {} snippets by_doc={}", len(snippets), by_doc)
    return state
