"""LLM-driven deck specification synthesis."""

import json
from typing import Any

from loguru import logger
from pydantic import ValidationError

from presentations.core.schemas import DeckSpec, GenerationMode, LayoutProfile
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

SYNTHESIS_SYSTEM_PROMPT = """You are a presentation architect. Given a content brief, optional source document,
and available slide layouts, produce a strict JSON deck specification.

Rules:
- The brief defines presentation intent, structure, and audience.
- When a source document is provided, ground slide content in its facts; do not copy large verbatim blocks;
  prefer concise bullet synthesis.
- If brief and source conflict, prefer the brief for structure and the source for factual accuracy.
- Use layout_index values from the provided layout profile only.
- Map content to ph_idx placeholder indices exactly as listed for each layout.
- ph_idx values are often non-sequential (for example 0, 10, 11). Never invent placeholder indices.
- For each slide, only use ph_idx values listed under allowed_ph_idx for that layout_index.
- Vary layouts across slides; avoid repeating the same layout for every slide.
- Keep bullet points concise; use \\n for line breaks within a placeholder.
- When the brief includes "Target length: N slides", produce approximately N slides.
- Return JSON matching the required schema with title and slides fields.
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
) -> str:
    """Build the user prompt for synthesis."""
    if layout:
        layout_json = _compact_layout(layout)
    else:
        layout_json = {"layouts": "Use MD3 scratch layouts"}

    parts = [f"Brief:\n{brief}\n"]
    if source_context:
        parts.append(f"Source document (grounding reference):\n{source_context}\n")
    parts.extend(
        [
            f"Generation mode: {mode.value}\n",
            f"Layout profile:\n{json.dumps(layout_json, indent=2)}\n",
            "Generate the complete deck JSON.",
        ]
    )
    return "\n".join(parts)


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
    user_prompt: str,
    max_retries: int,
    *,
    title: str | None,
    mode: GenerationMode,
    layout: LayoutProfile | None,
) -> DeckSpec:
    """Run synthesis attempts against a single provider."""
    from presentations.llm.ollama_provider import OllamaProvider

    last_error: Exception | None = None
    prompt = user_prompt
    for attempt in range(max_retries + 1):
        try:
            if isinstance(provider, OllamaProvider):
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
                f"{user_prompt}\n\nPrevious response was invalid: {exc}. "
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
    router = LLMRouter(synthesis_model_override=synthesis_model, allow_cloud=allow_cloud)
    providers = await router.get_synthesis_providers()
    user_prompt = _build_user_prompt(brief, layout, mode, source_context)

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
                user_prompt,
                max_retries,
                title=title,
                mode=mode,
                layout=layout,
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
