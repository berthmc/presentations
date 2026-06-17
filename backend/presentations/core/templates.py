"""Template library schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from presentations.core.schemas import GenerationMode, LayoutProfile


class TemplateRecord(BaseModel):
    """A persisted presentation template in the library."""

    id: str
    name: str
    file_path: str
    source_type: str
    layout_profile: LayoutProfile
    is_default: bool = False
    original_filename: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def summary(self) -> "TemplateSummary":
        """Return a lightweight view for list endpoints."""
        return TemplateSummary(
            id=self.id,
            name=self.name,
            source_type=self.source_type,
            is_default=self.is_default,
            layout_count=len(self.layout_profile.layouts),
            layout_names=self.layout_profile.layout_names()[:8],
            created_at=self.created_at,
        )


class TemplateSummary(BaseModel):
    """Lightweight template metadata for UI and MCP listing."""

    id: str
    name: str
    source_type: str
    is_default: bool
    layout_count: int
    layout_names: list[str] = Field(default_factory=list)
    created_at: datetime


class TemplateRegisterRequest(BaseModel):
    """Register a template by name (file supplied separately via multipart)."""

    name: str
    is_default: bool = False


class ResolvedTemplate(BaseModel):
    """Template resolved from id or path for generation."""

    template_id: str | None = None
    template_path: str
    layout_profile: LayoutProfile
    source_type: str

    @property
    def suggested_mode(self) -> GenerationMode:
        """Infer generation mode from template type."""
        if self.source_type == "pptx":
            return GenerationMode.TEMPLATE
        return GenerationMode.SCRATCH
