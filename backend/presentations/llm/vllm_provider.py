"""vLLM OpenAI-compatible local LLM provider."""

import json
from typing import Any

import httpx
from loguru import logger
from openai import AsyncOpenAI

from presentations.config.settings import get_settings
from presentations.llm.base import LLMProvider
from presentations.llm.ollama_provider import parse_json_content


class VLLMProvider(LLMProvider):
    """Local inference via vLLM OpenAI-compatible API."""

    name = "vllm"

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self.base_url = settings.vllm_base_url.rstrip("/")
        self.model = model or settings.vllm_model
        self.temperature = settings.ollama_temperature
        self.max_tokens = settings.ollama_num_predict
        self._timeout = settings.vllm_read_timeout
        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key="not-needed",
            timeout=self._timeout,
        )

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call vLLM chat completions with optional JSON schema response format."""
        response_format: dict[str, Any] | None = None
        if json_schema is not None:
            response_format = {"type": "json_schema", "json_schema": {"name": "response", "schema": json_schema}}

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format=response_format,
            )
        except Exception as exc:
            logger.error("vLLM request failed (model={}): {}", self.model, exc)
            raise RuntimeError(f"vLLM synthesis failed: {exc}") from exc

        content = response.choices[0].message.content or ""
        try:
            return parse_json_content(content)
        except json.JSONDecodeError as exc:
            raise ValueError("vLLM synthesis did not return valid JSON") from exc

    async def audit_slide_image(self, image_path: str, prompt: str) -> dict[str, Any]:
        """vLLM provider does not support vision in this pipeline."""
        raise NotImplementedError("vLLM provider does not support vision audit")

    @property
    def supports_vision(self) -> bool:
        return False

    async def is_available(self) -> bool:
        """Check whether vLLM OpenAI API is reachable."""
        settings = get_settings()
        if not settings.vllm_enabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url.replace('/v1', '')}/health")
                if response.status_code == 200:
                    return True
                response = await client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except httpx.HTTPError:
            return False
