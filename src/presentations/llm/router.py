"""Route LLM requests local-first with cloud fallback."""

from loguru import logger

from presentations.config.settings import get_settings
from presentations.core.profiles import resolve_effective_supports_vlm, resolve_model_profile
from presentations.llm.base import LLMProvider
from presentations.llm.gemini_provider import GeminiProvider
from presentations.llm.ollama_provider import OllamaProvider


class LLMRouter:
    """Select synthesis and vision providers based on availability."""

    def __init__(self) -> None:
        profile = resolve_model_profile()
        self.profile = profile
        self.local = OllamaProvider(
            synthesis_model=profile.synthesis_model,
            vlm_model=profile.vlm_model,
        )
        self.cloud = GeminiProvider()

    async def get_synthesis_provider(self) -> LLMProvider:
        """Return local Ollama if available, else Gemini."""
        if await self.local.is_available():
            logger.info("Using Ollama for synthesis ({})", self.local.synthesis_model)
            return self.local
        logger.warning("Ollama unavailable; falling back to Gemini")
        return self.cloud

    async def get_vision_provider(self) -> LLMProvider | None:
        """Return a vision-capable provider or None."""
        settings = get_settings()
        vlm_enabled = resolve_effective_supports_vlm(self.profile, settings)
        if vlm_enabled and await self.local.is_available():
            return self.local
        if self.cloud.is_configured():
            return self.cloud
        return None
