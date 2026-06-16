"""Pipeline state schema for the five-stage presentation agent orchestrator."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from presentations.core.schemas import DeckSpec, GenerateRequest, LayoutProfile, QAReport


class PipelineStage(StrEnum):
    """Named stages in the generation pipeline."""

    RESEARCH = "research"
    PROFILE = "profile"
    PLAN = "plan"
    ASSEMBLE = "assemble"
    INSPECT = "inspect"
    COMPLETE = "complete"


class ResearchSnippet(BaseModel):
    """One verified fact retrieved from source documents."""

    claim: str
    source_quote: str = ""
    doc_id: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    slide_topic_hint: str = ""


class ResearchPayload(BaseModel):
    """Structured research output from stage 1."""

    snippets: list[ResearchSnippet] = Field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Render snippets as compact grounding text for the Planner."""
        if not self.snippets:
            return ""
        lines = ["Structured research payload (verified reference snippets):"]
        for index, snippet in enumerate(self.snippets, start=1):
            lines.append(f"{index}. {snippet.claim}")
            if snippet.source_quote:
                lines.append(f"   Source: {snippet.source_quote}")
            if snippet.doc_id:
                lines.append(f"   Document: {snippet.doc_id}")
            if snippet.slide_topic_hint:
                lines.append(f"   Slide hint: {snippet.slide_topic_hint}")
        return "\n".join(lines)


class PipelineState(BaseModel):
    """Shared rigid state passed between agent stages."""

    request: GenerateRequest
    stage: PipelineStage = PipelineStage.RESEARCH
    research: ResearchPayload = Field(default_factory=ResearchPayload)
    layout_profile: LayoutProfile | None = None
    template_path: str | None = None
    mode: str | None = None
    deck_spec: DeckSpec | None = None
    output_path: str | None = None
    qa_report: QAReport | None = None
    revision: int = 0
    max_revisions: int = 3
    rollback_reasons: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
