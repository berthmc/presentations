"""Resolve template path, layout profile, and generation mode for a request."""

from presentations.config.settings import Settings, get_settings
from presentations.core.schemas import GenerateRequest, GenerationMode, LayoutProfile
from presentations.services.template_registry import get_template_registry


def resolve_generation_context(
    request: GenerateRequest,
) -> tuple[str | None, LayoutProfile | None, GenerationMode]:
    """Resolve template path, cached layout profile, and effective generation mode."""
    registry = get_template_registry()
    template_id = request.template_id
    template_path = request.template_path

    if request.mode == GenerationMode.TEMPLATE and not template_id and not template_path:
        default_pptx = registry.get_default_pptx()
        if default_pptx is not None:
            template_id = default_pptx.id

    resolved = registry.resolve(template_id=template_id, template_path=template_path)

    if resolved is None:
        if request.mode == GenerationMode.TEMPLATE:
            raise ValueError("template_id or template_path required for template mode")
        return None, None, request.mode

    mode = request.mode
    if request.template_id and mode == GenerationMode.SCRATCH and resolved.source_type == "pptx":
        mode = GenerationMode.TEMPLATE
    elif request.template_id and mode == GenerationMode.SCRATCH and resolved.source_type == "md":
        pass

    if mode == GenerationMode.TEMPLATE and resolved.source_type != "pptx":
        raise ValueError("Template mode requires a .pptx library template")

    if mode == GenerationMode.TEMPLATE and not resolved.template_path:
        raise ValueError("template_id or template_path required for template mode")

    return resolved.template_path, resolved.layout_profile, mode


def resolve_allow_cloud(request: GenerateRequest, settings: Settings | None = None) -> bool:
    """Return whether cloud LLM providers may be used for this request."""
    settings = settings or get_settings()
    return request.allow_cloud or settings.allow_cloud_llm_default
