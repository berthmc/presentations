"""Model catalog for synthesis provider selection."""

from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from presentations.config.settings import get_settings


@dataclass(frozen=True)
class CatalogModel:
    """A synthesis model exposed to the UI."""

    id: str
    label: str
    provider: str
    recommended_for: str
    speed: str
    quality: str
    notes: str


MODEL_CATALOG: tuple[CatalogModel, ...] = (
    CatalogModel(
        id="qwen2.5-coder:14b-awq",
        label="Qwen 2.5 Coder 14B AWQ (vLLM)",
        provider="vllm",
        recommended_for="Structured deck JSON, RTX 5060 Ti 16GB, agentic planning",
        speed="medium",
        quality="excellent",
        notes="Default planner on discrete GPU via vLLM OpenAI API.",
    ),
    CatalogModel(
        id="qwen2.5:7b",
        label="Qwen 2.5 7B (local)",
        provider="ollama",
        recommended_for="Technical decks, integrated GPUs, source-grounded content",
        speed="medium",
        quality="good",
        notes="Default on integrated profile. Better synthesis quality with 32k context.",
    ),
    CatalogModel(
        id="qwen2.5:3b",
        label="Qwen 2.5 3B (local)",
        provider="ollama",
        recommended_for="Quick drafts, low-memory hosts, short decks",
        speed="fast",
        quality="basic",
        notes="Fast iteration; best for simple topics and fewer slides.",
    ),
    CatalogModel(
        id="llama3.2:3b",
        label="Llama 3.2 3B (local)",
        provider="ollama",
        recommended_for="Lightweight drafts, alternative to Qwen 3B, short decks",
        speed="fast",
        quality="basic",
        notes="Compact Meta Llama model; good for quick iteration.",
    ),
    CatalogModel(
        id="gemini-2.0-flash",
        label="Gemini 2.0 Flash (cloud)",
        provider="gemini",
        recommended_for="Cloud fallback, long briefs, when Ollama is unavailable",
        speed="fast",
        quality="good",
        notes="Runs via Vertex AI / ADC. No local GPU required.",
    ),
)

GEMINI_MODEL_IDS: frozenset[str] = frozenset(
    entry.id for entry in MODEL_CATALOG if entry.provider == "gemini"
)

VLLM_MODEL_IDS: frozenset[str] = frozenset(
    entry.id for entry in MODEL_CATALOG if entry.provider == "vllm"
)


def is_gemini_model_id(model_id: str) -> bool:
    """Return True when the model id targets the Gemini provider."""
    return model_id.startswith("gemini") or model_id in GEMINI_MODEL_IDS


def is_vllm_model_id(model_id: str) -> bool:
    """Return True when the model id targets the vLLM provider."""
    return model_id in VLLM_MODEL_IDS or model_id.startswith("qwen2.5-coder")


async def _fetch_ollama_model_names() -> set[str]:
    """Return installed Ollama model names from /api/tags."""
    settings = get_settings()
    host = settings.ollama_host.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{host}/api/tags")
            if response.status_code != 200:
                return set()
            data = response.json()
            return {model.get("name", "") for model in data.get("models", []) if model.get("name")}
    except httpx.HTTPError as exc:
        logger.warning("Failed to list Ollama models: {}", exc)
        return set()


async def _vllm_is_reachable() -> bool:
    """Return True when the vLLM OpenAI API responds."""
    from presentations.llm.vllm_provider import VLLMProvider

    provider = VLLMProvider()
    return await provider.is_available()


async def _ollama_is_reachable() -> bool:
    """Return True when the Ollama HTTP API responds."""
    settings = get_settings()
    host = settings.ollama_host.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{host}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


def _ollama_model_installed(model_id: str, installed: set[str]) -> bool:
    """Return True when an Ollama model id matches an installed tag."""
    if model_id in installed:
        return True
    base_name = model_id.split(":")[0]
    return any(name == base_name or name.startswith(f"{base_name}:") for name in installed)


def _gemini_available() -> bool:
    """Return True when Gemini cloud synthesis is likely configured."""
    settings = get_settings()
    return bool(settings.google_cloud_project)


async def list_available_models() -> dict[str, Any]:
    """Return the synthesis model catalog with availability flags."""
    installed = await _fetch_ollama_model_names()
    ollama_reachable = await _ollama_is_reachable()
    vllm_reachable = await _vllm_is_reachable()
    models: list[dict[str, Any]] = []

    for entry in MODEL_CATALOG:
        if entry.provider == "ollama":
            available = ollama_reachable and _ollama_model_installed(entry.id, installed)
        elif entry.provider == "vllm":
            available = vllm_reachable
        else:
            available = _gemini_available()

        models.append(
            {
                "id": entry.id,
                "label": entry.label,
                "provider": entry.provider,
                "recommended_for": entry.recommended_for,
                "speed": entry.speed,
                "quality": entry.quality,
                "notes": entry.notes,
                "available": available,
            }
        )

    return {"default": "auto", "models": models}
