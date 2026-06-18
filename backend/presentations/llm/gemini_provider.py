"""Google Gemini cloud fallback provider."""

import json
import time
from pathlib import Path
from typing import Any

from loguru import logger

from presentations.config.pipeline_logging import log_llm_call
from presentations.config.settings import get_settings
from presentations.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini / Vertex AI fallback provider."""

    name = "gemini"

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self.model = model or settings.gemini_model
        self.vision_model = settings.gemini_vision_model
        self.project = settings.google_cloud_project
        self.location = settings.google_cloud_location
        self._client = None

    def _get_client(self):
        """Lazy-init google-genai client."""
        if self._client is None:
            from google import genai

            if self.project:
                self._client = genai.Client(vertexai=True, project=self.project, location=self.location)
            else:
                self._client = genai.Client()
        return self._client

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate JSON via Gemini."""
        client = self._get_client()
        prompt = f"{system_prompt}\n\n{user_prompt}\n\nRespond with valid JSON only."
        prompt_chars = len(prompt)
        started = time.perf_counter()
        response = client.models.generate_content(model=self.model, contents=prompt)
        duration_s = time.perf_counter() - started
        text = response.text or "{}"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end])
            else:
                logger.error("Gemini returned invalid JSON: {}", text[:500])
                raise ValueError("Gemini synthesis did not return valid JSON")
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        completion_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        log_llm_call(
            provider=self.name,
            model=self.model,
            duration_s=duration_s,
            prompt_chars=prompt_chars,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return parsed

    async def audit_slide_image(self, image_path: str, prompt: str) -> dict[str, Any]:
        """Audit slide image with Gemini vision."""
        from google.genai import types

        client = self._get_client()
        image_bytes = Path(image_path).read_bytes()
        part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        response = client.models.generate_content(
            model=self.vision_model,
            contents=[prompt, part],
        )
        text = response.text or '{"passed": false, "reasons": ["No response"]}'
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"passed": False, "reasons": [text[:500]]}

    @property
    def supports_vision(self) -> bool:
        return True

    def is_configured(self) -> bool:
        """Return True when Gemini can be used."""
        return bool(self.project) or True  # ADC may work without explicit project
