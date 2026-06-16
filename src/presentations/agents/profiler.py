"""Stage 2: Template layout introspection (Structural Profiler)."""

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
    template_path, layout_profile, mode = resolve_generation_context(state.request)
    state.template_path = template_path
    state.layout_profile = layout_profile
    state.mode = mode.value
    return state


def discover_layout_from_path(template_path: str):
    """Expose layout discovery for API/MCP compatibility."""
    return discover_layout(template_path)
