"""Ollama local LLM provider."""

import base64
import json
import time
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from presentations.config.pipeline_logging import log_llm_call
from presentations.config.settings import get_settings
from presentations.llm.base import LLMProvider


def parse_json_content(content: str) -> dict[str, Any]:
    """Parse JSON from model output, with brace-slicing recovery."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        raise


class OllamaProvider(LLMProvider):
    """Local inference via Ollama HTTP API."""

    name = "ollama"

    def __init__(self, synthesis_model: str | None = None, vlm_model: str | None = None) -> None:
        settings = get_settings()
        self.host = settings.ollama_host.rstrip("/")
        self.synthesis_model = synthesis_model or settings.ollama_synthesis_model
        self.vlm_model = vlm_model or settings.ollama_vlm_model
        self.num_predict = settings.ollama_num_predict
        self.num_ctx = settings.ollama_num_ctx
        self.temperature = settings.ollama_temperature
        self._timeout_generate = httpx.Timeout(connect=10.0, read=settings.ollama_read_timeout_generate, write=30.0, pool=5.0)
        self._timeout_vlm = httpx.Timeout(connect=10.0, read=settings.ollama_read_timeout_vlm, write=30.0, pool=5.0)

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call Ollama chat API and parse JSON response."""
        payload: dict[str, Any] = {
            "model": self.synthesis_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": json_schema if json_schema is not None else "json",
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
                "num_ctx": self.num_ctx,
            },
        }
        prompt_chars = len(system_prompt) + len(user_prompt)
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_generate) as client:
                response = await client.post(f"{self.host}/api/chat", json=payload)
                response.raise_for_status()
                body = response.json()
                content = body["message"]["content"]
        except httpx.TimeoutException as exc:
            logger.error(
                "Ollama timeout after {}s generating JSON with model={}",
                self._timeout_generate.read,
                self.synthesis_model,
            )
            raise TimeoutError(
                f"Ollama did not respond within {self._timeout_generate.read}s. "
                "Increase OLLAMA_READ_TIMEOUT_GENERATE or switch to a faster model."
            ) from exc
        except httpx.TransportError as exc:
            logger.error("Ollama transport error generating JSON with model={}: {}", self.synthesis_model, exc)
            raise RuntimeError(f"Ollama unreachable at {self.host}: {exc}") from exc
        duration_s = time.perf_counter() - started
        try:
            parsed = parse_json_content(content)
        except json.JSONDecodeError as exc:
            done_reason = body.get("done_reason", "unknown")
            eval_count = body.get("eval_count", 0)
            prompt_eval_count = body.get("prompt_eval_count", 0)
            logger.error(
                "Ollama returned invalid JSON (done_reason={}, eval_count={}, prompt_eval_count={}): {}",
                done_reason,
                eval_count,
                prompt_eval_count,
                content[:500],
            )
            raise ValueError("Ollama synthesis did not return valid JSON") from exc
        log_llm_call(
            provider=self.name,
            model=self.synthesis_model,
            duration_s=duration_s,
            prompt_chars=prompt_chars,
            prompt_tokens=body.get("prompt_eval_count"),
            completion_tokens=body.get("eval_count"),
        )
        return parsed

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
        try:
            async with httpx.AsyncClient(timeout=self._timeout_vlm) as client:
                response = await client.post(f"{self.host}/api/chat", json=payload)
                response.raise_for_status()
                content = response.json()["message"]["content"]
        except httpx.TimeoutException as exc:
            logger.error(
                "Ollama timeout after {}s during VLM audit with model={}",
                self._timeout_vlm.read,
                self.vlm_model,
            )
            raise TimeoutError(
                f"Ollama VLM did not respond within {self._timeout_vlm.read}s. "
                "Increase OLLAMA_READ_TIMEOUT_VLM or switch to a faster model."
            ) from exc
        except httpx.TransportError as exc:
            logger.error("Ollama transport error during VLM audit with model={}: {}", self.vlm_model, exc)
            raise RuntimeError(f"Ollama unreachable at {self.host}: {exc}") from exc
        return parse_json_content(content)

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
