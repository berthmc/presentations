"""LLM provider protocol."""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract LLM provider."""

    name: str = "base"

    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate a JSON object from prompts."""

    @abstractmethod
    async def audit_slide_image(self, image_path: str, prompt: str) -> dict[str, Any]:
        """Audit a slide image and return structured findings."""

    @property
    def supports_vision(self) -> bool:
        """Whether this provider can analyse images."""
        return False
