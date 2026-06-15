"""Ollama local LLM provider."""

import base64
import json
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from presentations.config.settings import get_settings
from presentations.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Local inference via Ollama HTTP API."""

    name = "ollama"

    def __init__(self, synthesis_model: str | None = None, vlm_model: str | None = None) -> None:
        settings = get_settings()
        self.host = settings.ollama_host.rstrip("/")
        self.synthesis_model = synthesis_model or settings.ollama_synthesis_model
        self.vlm_model = vlm_model or settings.ollama_vlm_model

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Call Ollama chat API and parse JSON response."""
        payload = {
            "model": self.synthesis_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.host}/api/chat", json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Ollama returned invalid JSON: {}", content[:500])
            raise ValueError("Ollama synthesis did not return valid JSON") from exc

    async def audit_slide_image(self, image_path: str, prompt: str) -> dict[str, Any]:
        """Run VLM audit on a slide image via Ollama."""
        image_bytes = Path(image_path).read_bytes()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.vlm_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [encoded],
                }
            ],
            "format": "json",
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{self.host}/api/chat", json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
        return json.loads(content)

    @property
    def supports_vision(self) -> bool:
        return True

    async def is_available(self) -> bool:
        """Check whether Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False
