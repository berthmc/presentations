"""Pydantic schemas for layout discovery, deck synthesis, and QA."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GenerationMode(StrEnum):
    """How the deck should be compiled."""

    TEMPLATE = "template"
    SCRATCH = "scratch"


class PlaceholderInfo(BaseModel):
    """A placeholder discovered on a slide layout."""

    index: int
    name: str
    type: str


class LayoutEntry(BaseModel):
    """One slide layout from a template."""

    name: str
    placeholders: list[PlaceholderInfo]


class LayoutProfile(BaseModel):
    """Machine-readable layout map from template discovery."""

    source_path: str
    source_type: str = "pptx"
    layouts: dict[int, LayoutEntry]
    theme: dict[str, Any] = Field(default_factory=dict)

    def layout_names(self) -> list[str]:
        """Return human-readable layout names in index order."""
        return [self.layouts[idx].name for idx in sorted(self.layouts.keys())]


class PlaceholderMapping(BaseModel):
    """Content mapped to a placeholder index."""

    ph_idx: int
    content: str


class SlideSpec(BaseModel):
    """One slide in the generated deck."""

    layout_index: int
    mappings: list[PlaceholderMapping] = Field(default_factory=list)
    notes: str | None = None


class DeckSpec(BaseModel):
    """Strict JSON schema the LLM must produce."""

    title: str = "Untitled Presentation"
    mode: GenerationMode = GenerationMode.TEMPLATE
    slides: list[SlideSpec]

    def to_prompt_example(self) -> str:
        """Return a JSON example for LLM prompting."""
        return self.model_dump_json(indent=2, exclude_none=True)


class QAIssue(BaseModel):
    """A single visual or content QA finding."""

    slide: int
    severity: str = "warning"
    category: str
    message: str


class QAReport(BaseModel):
    """Result of visual QA on a rendered deck."""

    passed: bool
    reasons: list[str] = Field(default_factory=list)
    issues: list[QAIssue] = Field(default_factory=list)
    slide_images: list[str] = Field(default_factory=list)
    iterations: int = 1

    @classmethod
    def from_vlm_response(cls, slide: int, payload: dict[str, Any], slide_images: list[str]) -> "QAReport":
        """Build a report from a VLM JSON response."""
        passed = bool(payload.get("passed", False))
        reasons = list(payload.get("reasons", []))
        issues = [
            QAIssue(slide=slide, severity="error", category="vlm", message=reason)
            for reason in reasons
        ]
        return cls(passed=passed, reasons=reasons, issues=issues, slide_images=slide_images)


class GenerateRequest(BaseModel):
    """API/MCP request to generate a presentation."""

    brief: str
    template_id: str | None = None
    template_path: str | None = None
    mode: GenerationMode = GenerationMode.SCRATCH
    title: str | None = None
    run_qa: bool = True
    synthesis_model: str | None = None
    source_context: str | None = None
    allow_cloud: bool = False


class GenerateResult(BaseModel):
    """Output of a full generation pipeline."""

    output_path: str
    deck_spec: DeckSpec
    qa_report: QAReport | None = None
    layout_profile: LayoutProfile | None = None
