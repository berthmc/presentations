"""LLM-driven deck specification synthesis."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from pydantic import ValidationError

from presentations.config.settings import Settings, get_settings
from presentations.core.schemas import (
    DeckSpec,
    DigestEntry,
    GenerationMode,
    LayoutProfile,
    SourceDigest,
)
from presentations.llm.base import LLMProvider
from presentations.llm.layout_validate import validate_deck_against_layout
from presentations.llm.router import LLMRouter

DECK_SYNTHESIS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "layout_index": {"type": "integer"},
                    "mappings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ph_idx": {"type": "integer"},
                                "content": {"type": "string"},
                            },
                            "required": ["ph_idx", "content"],
                        },
                    },
                },
                "required": ["layout_index", "mappings"],
            },
        },
    },
    "required": ["title", "slides"],
}

DIGEST_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "source_quote": {"type": "string"},
                    "slide_topic_hint": {"type": "string"},
                },
                "required": ["claim"],
            },
        }
    },
    "required": ["facts"],
}

SYNTHESIS_SYSTEM_PROMPT = """You are a presentation architect. Given a content brief, optional source document,
and available slide layouts, produce a strict JSON deck specification.

Rules:
- The brief defines presentation intent, structure, and audience.
- When a source document or structured digest is provided, ground slide content in its facts.
- Extract specific facts, numbers, terminology, and technical details from the source and place them
  on the appropriate slides.
- When source documents are provided with '--- Document: name ---' or '--- Context7: name ---' separators,
  synthesise content across all documents; attribute facts to the source where relevant.
- If brief and source conflict, prefer the brief for structure and the source for factual accuracy.
- When a source document or digest is present, every content slide must reference at least one specific
  fact, figure, metric, or concept drawn from it.
- Use layout_index values from the provided layout profile only.
- Map content to ph_idx placeholder indices exactly as listed for each layout.
- ph_idx values are often non-sequential (for example 0, 10, 11). Never invent placeholder indices.
- For each slide, only use ph_idx values listed under allowed_ph_idx for that layout_index.
- Vary layouts across slides; avoid repeating the same layout for every slide.
- Keep bullet points concise but substantive; use \\n for line breaks within a placeholder.
- When the brief includes "Target length: N slides", produce approximately N slides.
- Return JSON matching the required schema with title and slides fields.
"""

DIGEST_SYSTEM_PROMPT = """You are a technical analyst preparing source material for a presentation.
Extract the most important facts, statistics, concepts, and architectural components from the
provided source text.

Rules:
- Return strict JSON with a facts array.
- Each fact must include claim (required), source_quote (short supporting excerpt), and
  slide_topic_hint (which slide theme the fact supports).
- Prefer concrete details: numbers, product names, protocols, latency figures, deployment patterns.
- Do not invent facts not supported by the source text.
- Produce up to 20 facts per chunk.
"""


def _compact_layout(layout: LayoutProfile) -> dict[str, Any]:
    """Return a token-efficient layout summary for synthesis prompts."""
    return {
        "layouts": [
            {
                "layout_index": idx,
                "name": entry.name,
                "allowed_ph_idx": [ph.index for ph in entry.placeholders],
                "placeholders": [{"ph_idx": ph.index, "name": ph.name} for ph in entry.placeholders],
            }
            for idx, entry in sorted(layout.layouts.items())
        ]
    }


def _build_user_prompt(
    brief: str,
    layout: LayoutProfile | None,
    mode: GenerationMode,
    source_context: str | None = None,
    max_source_chars: int | None = None,
) -> str:
    """Build the user prompt for synthesis."""
    if layout:
        layout_json = _compact_layout(layout)
    else:
        layout_json = {"layouts": "Use MD3 scratch layouts"}

    parts = [f"Brief:\n{brief}\n"]
    if source_context:
        ctx = source_context
        if max_source_chars is not None and len(source_context) > max_source_chars:
            ctx = source_context[:max_source_chars]
            ctx += f"\n[Source truncated to {max_source_chars} chars for local model]"
        parts.append(f"Source document (grounding reference):\n{ctx}\n")
    parts.extend(
        [
            f"Generation mode: {mode.value}\n",
            f"Layout profile:\n{json.dumps(layout_json, indent=2)}\n",
            "Generate the complete deck JSON.",
        ]
    )
    return "\n".join(parts)


def _build_digest_user_prompt(source_chunk: str, brief: str) -> str:
    """Build the user prompt for the digest phase."""
    return (
        f"Brief (for relevance):\n{brief}\n\n"
        f"Source chunk:\n{source_chunk}\n\n"
        "Extract the most important presentation-ready facts as JSON."
    )


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split long source text into overlapping-free chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += chunk_size
    return chunks


def _merge_digests(digests: list[SourceDigest]) -> SourceDigest:
    """Merge digest chunks and deduplicate facts by claim text."""
    seen: set[str] = set()
    merged: list[DigestEntry] = []
    for digest in digests:
        for fact in digest.facts:
            key = fact.claim.strip().casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(fact)
    return SourceDigest(facts=merged)


def _provider_supports_json_schema(provider: LLMProvider) -> bool:
    """Return True when the provider accepts a JSON schema response format."""
    from presentations.llm.ollama_provider import OllamaProvider
    from presentations.llm.vllm_provider import VLLMProvider

    return isinstance(provider, (OllamaProvider, VLLMProvider))


async def _digest_chunk_with_provider(
    provider: LLMProvider,
    *,
    brief: str,
    source_chunk: str,
) -> SourceDigest:
    """Run digest extraction for a single source chunk."""
    user_prompt = _build_digest_user_prompt(source_chunk, brief)
    if _provider_supports_json_schema(provider):
        payload = await provider.generate_json(
            DIGEST_SYSTEM_PROMPT,
            user_prompt,
            json_schema=DIGEST_JSON_SCHEMA,
        )
    else:
        payload = await provider.generate_json(DIGEST_SYSTEM_PROMPT, user_prompt)
    return SourceDigest.model_validate(payload)


async def digest_source_context(
    source_context: str,
    brief: str,
    *,
    synthesis_model: str | None = None,
    allow_cloud: bool = False,
    settings: Settings | None = None,
) -> SourceDigest:
    """Extract structured facts from source material before deck synthesis."""
    settings = settings or get_settings()
    router = LLMRouter(synthesis_model_override=synthesis_model, allow_cloud=allow_cloud)
    providers = await router.get_synthesis_providers()
    if not providers:
        raise ValueError("No synthesis providers available for digest phase")

    chunks = _chunk_text(source_context, settings.digest_chunk_chars)
    provider = providers[0]
    digests: list[SourceDigest] = []

    for index, chunk in enumerate(chunks, start=1):
        try:
            digest = await _digest_chunk_with_provider(provider, brief=brief, source_chunk=chunk)
            digests.append(digest)
            logger.info(
                "Digest chunk {}/{} produced {} facts via {}",
                index,
                len(chunks),
                len(digest.facts),
                provider.name,
            )
        except (ValidationError, ValueError, KeyError) as exc:
            logger.warning("Digest chunk {} failed: {}", index, exc)

    return _merge_digests(digests)


async def _prepare_source_context(
    source_context: str | None,
    brief: str,
    *,
    synthesis_model: str | None,
    allow_cloud: bool,
    settings: Settings,
) -> str | None:
    """Optionally digest raw source context into compact grounding text."""
    if not source_context or not settings.enable_digest_phase:
        return source_context

    digest = await digest_source_context(
        source_context,
        brief,
        synthesis_model=synthesis_model,
        allow_cloud=allow_cloud,
        settings=settings,
    )
    digest_text = digest.to_prompt_text()
    if not digest_text:
        logger.warning("Digest phase returned no facts; using raw source context")
        return source_context

    logger.info("Using structured digest with {} facts for synthesis", len(digest.facts))
    return digest_text


def _payload_to_deck(
    payload: dict[str, Any],
    *,
    title: str | None,
    mode: GenerationMode,
    layout: LayoutProfile | None,
) -> DeckSpec:
    """Validate LLM payload and enforce layout constraints for template mode."""
    if title:
        payload["title"] = title
    payload["mode"] = mode.value
    deck = DeckSpec.model_validate(payload)
    if layout and mode == GenerationMode.TEMPLATE:
        validate_deck_against_layout(deck, layout)
    return deck


async def _generate_with_provider(
    provider: LLMProvider,
    max_retries: int,
    *,
    brief: str,
    layout: LayoutProfile | None,
    mode: GenerationMode,
    source_context: str | None,
    title: str | None,
) -> DeckSpec:
    """Run synthesis attempts against a single provider."""
    settings = get_settings()
    from presentations.llm.ollama_provider import OllamaProvider

    max_src = settings.ollama_max_source_context_chars if isinstance(provider, OllamaProvider) else None
    base_prompt = _build_user_prompt(brief, layout, mode, source_context, max_source_chars=max_src)

    last_error: Exception | None = None
    prompt = base_prompt
    for attempt in range(max_retries + 1):
        try:
            if _provider_supports_json_schema(provider):
                payload = await provider.generate_json(
                    SYNTHESIS_SYSTEM_PROMPT,
                    prompt,
                    json_schema=DECK_SYNTHESIS_JSON_SCHEMA,
                )
            else:
                payload = await provider.generate_json(SYNTHESIS_SYSTEM_PROMPT, prompt)
            return _payload_to_deck(payload, title=title, mode=mode, layout=layout)
        except (ValidationError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning(
                "Deck synthesis attempt {} with {} failed: {}",
                attempt + 1,
                provider.name,
                exc,
            )
            prompt = (
                f"{base_prompt}\n\nPrevious response was invalid: {exc}. "
                "Fix the JSON and return a valid deck specification. "
                "Use only layout_index and ph_idx values from the layout profile."
            )
    raise ValueError(
        f"Provider {provider.name} failed after {max_retries + 1} attempts"
    ) from last_error


async def synthesize_deck_spec(
    brief: str,
    layout: LayoutProfile | None = None,
    mode: GenerationMode = GenerationMode.TEMPLATE,
    title: str | None = None,
    source_context: str | None = None,
    synthesis_model: str | None = None,
    allow_cloud: bool = False,
    max_retries: int = 2,
) -> DeckSpec:
    """Synthesize a validated DeckSpec from a brief via LLM.

    Args:
        brief: User content brief.
        layout: Discovered layout profile (optional for scratch mode).
        mode: Template or scratch generation.
        title: Optional deck title override.
        source_context: Optional PDF-derived text for factual grounding.
        synthesis_model: Optional synthesis model override (Ollama tag or Gemini id).
        allow_cloud: When True, Gemini may be used as fallback or when Ollama is unavailable.
        max_retries: Number of repair attempts on validation failure per provider.

    Returns:
        Validated DeckSpec.
    """
    settings = get_settings()
    prepared_source = await _prepare_source_context(
        source_context,
        brief,
        synthesis_model=synthesis_model,
        allow_cloud=allow_cloud,
        settings=settings,
    )

    router = LLMRouter(synthesis_model_override=synthesis_model, allow_cloud=allow_cloud)
    providers = await router.get_synthesis_providers()

    last_error: Exception | None = None
    for provider_index, provider in enumerate(providers):
        if provider_index > 0:
            logger.warning(
                "Falling back to {} ({}) for deck synthesis",
                provider.name,
                getattr(provider, "model", getattr(provider, "synthesis_model", "unknown")),
            )
        try:
            deck = await _generate_with_provider(
                provider,
                max_retries,
                brief=brief,
                layout=layout,
                mode=mode,
                source_context=prepared_source,
                title=title,
            )
            logger.info("Synthesized deck with {} slides via {}", len(deck.slides), provider.name)
            return deck
        except (ValidationError, ValueError, KeyError) as exc:
            last_error = exc
            if provider_index < len(providers) - 1:
                continue
            raise ValueError(
                f"Failed to synthesize deck after trying {len(providers)} provider(s)"
            ) from last_error

    raise ValueError("Failed to synthesize deck: no synthesis providers available") from last_error
