"""Stage 2: Template layout introspection (Structural Profiler)."""

from loguru import logger

from presentations.core.state import PipelineState
from presentations.ingest.discover import discover_layout
from presentations.services.generation_context import resolve_generation_context


async def run_profiler(state: PipelineState) -> PipelineState:
    """Discover layout manifest from the resolved template.

    Args:
        state: Pipeline state with request populated.

    Returns:
        Updated state with layout_profile and template_path.
    """
    request = state.request
    template_path, layout_profile, mode = resolve_generation_context(request)
    state.template_path = template_path
    state.layout_profile = layout_profile
    state.mode = mode.value

    template_ref = request.template_id or template_path or "scratch"
    layout_count = len(layout_profile.layouts) if layout_profile and layout_profile.layouts else 0
    placeholder_count = (
        sum(len(entry.placeholders) for entry in layout_profile.layouts.values())
        if layout_profile and layout_profile.layouts
        else 0
    )
    logger.info(
        "Profiler resolved mode={} template={} layouts={} placeholders={}",
        mode.value,
        template_ref,
        layout_count,
        placeholder_count,
    )
    return state


def discover_layout_from_path(template_path: str):
    """Expose layout discovery for API/MCP compatibility."""
    return discover_layout(template_path)
