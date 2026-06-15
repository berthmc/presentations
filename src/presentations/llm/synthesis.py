"""LLM-driven deck specification synthesis."""

import json

from loguru import logger
from pydantic import ValidationError

from presentations.core.schemas import DeckSpec, GenerationMode, LayoutProfile
from presentations.llm.router import LLMRouter

SYNTHESIS_SYSTEM_PROMPT = """You are a presentation architect. Given a content brief and available slide layouts,
produce a strict JSON deck specification.

Rules:
- Use layout_index values from the provided layout profile only.
- Map content to ph_idx placeholder indices exactly as listed.
- Vary layouts across slides; avoid repeating the same layout for every slide.
- Keep bullet points concise; use \\n for line breaks within a placeholder.
- When the brief includes "Target length: N slides", produce approximately N slides.
- Return JSON matching this schema:
{
  "title": "string",
  "mode": "template" | "scratch",
  "slides": [
    {
      "layout_index": 0,
      "mappings": [{"ph_idx": 0, "content": "..."}]
    }
  ]
}
"""


def _build_user_prompt(brief: str, layout: LayoutProfile | None, mode: GenerationMode) -> str:
    """Build the user prompt for synthesis."""
    layout_json = layout.model_dump() if layout else {"layouts": "Use MD3 scratch layouts"}
    return (
        f"Brief:\n{brief}\n\n"
        f"Generation mode: {mode.value}\n\n"
        f"Layout profile:\n{json.dumps(layout_json, indent=2)}\n\n"
        "Generate the complete deck JSON."
    )


async def synthesize_deck_spec(
    brief: str,
    layout: LayoutProfile | None = None,
    mode: GenerationMode = GenerationMode.TEMPLATE,
    title: str | None = None,
    synthesis_model: str | None = None,
    max_retries: int = 2,
) -> DeckSpec:
    """S synthesize a validated DeckSpec from a brief via LLM.

    Args:
        brief: User content brief.
        layout: Discovered layout profile (optional for scratch mode).
        mode: Template or scratch generation.
        title: Optional deck title override.
        synthesis_model: Optional synthesis model override (Ollama tag or Gemini id).
        max_retries: Number of repair attempts on validation failure.

    Returns:
        Validated DeckSpec.
    """
    router = LLMRouter(synthesis_model_override=synthesis_model)
    provider = await router.get_synthesis_provider()
    user_prompt = _build_user_prompt(brief, layout, mode)

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            payload = await provider.generate_json(SYNTHESIS_SYSTEM_PROMPT, user_prompt)
            if title:
                payload["title"] = title
            payload["mode"] = mode.value
            deck = DeckSpec.model_validate(payload)
            logger.info("Synthesized deck with {} slides", len(deck.slides))
            return deck
        except (ValidationError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning("Deck synthesis attempt {} failed: {}", attempt + 1, exc)
            user_prompt = (
                f"{user_prompt}\n\nPrevious response was invalid: {exc}. "
                "Fix the JSON and return a valid deck specification."
            )

    raise ValueError(f"Failed to synthesize deck after {max_retries + 1} attempts") from last_error
