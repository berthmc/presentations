"""Route LLM requests local-first with cloud fallback."""

from loguru import logger

from presentations.config.settings import get_settings
from presentations.core.profiles import resolve_effective_supports_vlm, resolve_model_profile
from presentations.llm.base import LLMProvider
from presentations.llm.catalog import is_gemini_model_id
from presentations.llm.gemini_provider import GeminiProvider
from presentations.llm.ollama_provider import OllamaProvider

_CLOUD_DISABLED_MSG = (
    "Ollama is unreachable and cloud LLM is disabled. "
    "Enable 'Allow Gemini' in the UI or check that Ollama is running."
)


class LLMRouter:
    """Select synthesis and vision providers based on availability."""

    def __init__(
        self,
        synthesis_model_override: str | None = None,
        allow_cloud: bool = False,
    ) -> None:
        profile = resolve_model_profile()
        self.profile = profile
        settings = get_settings()
        ollama_synthesis = profile.synthesis_model
        gemini_model = settings.gemini_model
        self._prefer_gemini = False
        self.allow_cloud = allow_cloud

        if synthesis_model_override:
            if is_gemini_model_id(synthesis_model_override):
                gemini_model = synthesis_model_override
                self._prefer_gemini = True
            else:
                ollama_synthesis = synthesis_model_override

        self.local = OllamaProvider(
            synthesis_model=ollama_synthesis,
            vlm_model=profile.vlm_model,
        )
        self.cloud = GeminiProvider(model=gemini_model)

    async def get_synthesis_provider(self) -> LLMProvider:
        """Return the synthesis provider honoring an explicit override when set."""
        providers = await self.get_synthesis_providers()
        return providers[0]

    async def get_synthesis_providers(self) -> list[LLMProvider]:
        """Return ordered synthesis providers, including cloud fallback when consented."""
        providers: list[LLMProvider] = []

        if self._prefer_gemini and self.cloud.is_configured():
            logger.info("Using Gemini for synthesis ({})", self.cloud.model)
            providers.append(self.cloud)
            return providers

        if await self.local.is_available():
            logger.info("Using Ollama for synthesis ({})", self.local.synthesis_model)
            providers.append(self.local)
            if self.allow_cloud and self.cloud.is_configured():
                providers.append(self.cloud)
            return providers

        if not self.allow_cloud:
            raise RuntimeError(_CLOUD_DISABLED_MSG)

        logger.warning("Ollama unavailable; falling back to Gemini")
        providers.append(self.cloud)
        return providers

    async def get_vision_provider(self) -> LLMProvider | None:
        """Return a vision-capable provider or None."""
        settings = get_settings()
        vlm_enabled = resolve_effective_supports_vlm(self.profile, settings)
        if vlm_enabled and await self.local.is_available():
            return self.local
        if self.allow_cloud and self.cloud.is_configured():
            return self.cloud
        return None
