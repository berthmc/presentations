"""Tests for LLM router cloud consent gating."""

from unittest.mock import AsyncMock, patch

import pytest

from presentations.llm.router import LLMRouter


@pytest.mark.asyncio
async def test_synthesis_providers_local_only_when_cloud_disabled() -> None:
    router = LLMRouter(allow_cloud=False)
    with (
        patch.object(router.local, "is_available", new=AsyncMock(return_value=True)),
        patch.object(router.cloud, "is_configured", return_value=True),
    ):
        providers = await router.get_synthesis_providers()

    assert len(providers) == 1
    assert providers[0].name == "ollama"


@pytest.mark.asyncio
async def test_synthesis_providers_include_gemini_fallback_when_cloud_allowed() -> None:
    router = LLMRouter(allow_cloud=True)
    with (
        patch.object(router.local, "is_available", new=AsyncMock(return_value=True)),
        patch.object(router.cloud, "is_configured", return_value=True),
    ):
        providers = await router.get_synthesis_providers()

    assert len(providers) == 2
    assert providers[0].name == "ollama"
    assert providers[1].name == "gemini"


@pytest.mark.asyncio
async def test_synthesis_providers_raises_when_ollama_down_and_cloud_disabled() -> None:
    router = LLMRouter(allow_cloud=False)
    with patch.object(router.local, "is_available", new=AsyncMock(return_value=False)):
        with pytest.raises(RuntimeError, match="cloud LLM is disabled"):
            await router.get_synthesis_providers()


@pytest.mark.asyncio
async def test_synthesis_providers_gemini_only_when_ollama_down_and_cloud_allowed() -> None:
    router = LLMRouter(allow_cloud=True)
    with (
        patch.object(router.local, "is_available", new=AsyncMock(return_value=False)),
        patch.object(router.cloud, "is_configured", return_value=True),
    ):
        providers = await router.get_synthesis_providers()

    assert len(providers) == 1
    assert providers[0].name == "gemini"


@pytest.mark.asyncio
async def test_synthesis_providers_explicit_gemini_model_ignores_cloud_flag() -> None:
    router = LLMRouter(synthesis_model_override="gemini-2.5-pro", allow_cloud=False)
    with (
        patch.object(router.local, "is_available", new=AsyncMock(return_value=True)),
        patch.object(router.cloud, "is_configured", return_value=True),
    ):
        providers = await router.get_synthesis_providers()

    assert len(providers) == 1
    assert providers[0].name == "gemini"


@pytest.mark.asyncio
async def test_vision_provider_returns_none_when_local_unavailable_and_cloud_disabled() -> None:
    router = LLMRouter(allow_cloud=False)
    with (
        patch("presentations.llm.router.resolve_effective_supports_vlm", return_value=True),
        patch.object(router.local, "is_available", new=AsyncMock(return_value=False)),
        patch.object(router.cloud, "is_configured", return_value=True),
    ):
        provider = await router.get_vision_provider()

    assert provider is None


@pytest.mark.asyncio
async def test_vision_provider_returns_gemini_when_local_unavailable_and_cloud_allowed() -> None:
    router = LLMRouter(allow_cloud=True)
    with (
        patch("presentations.llm.router.resolve_effective_supports_vlm", return_value=True),
        patch.object(router.local, "is_available", new=AsyncMock(return_value=False)),
        patch.object(router.cloud, "is_configured", return_value=True),
    ):
        provider = await router.get_vision_provider()

    assert provider is not None
    assert provider.name == "gemini"
