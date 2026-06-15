"""FastMCP server exposing presentation generation tools."""

import argparse
import json
from pathlib import Path

from fastmcp import FastMCP
from loguru import logger

from presentations.config.logging_config import configure_logging
from presentations.config.settings import get_settings
from presentations.core.profiles import run_hardware_diagnostics
from presentations.core.schemas import GenerateRequest, GenerationMode
from presentations.ingest.discover import discover_layout
from presentations.qa.loop import run_qa_loop
from presentations.services.pipeline import generate_presentation
from presentations.services.template_registry import get_template_registry

mcp = FastMCP(
    name="pptx-engine",
    instructions=(
        "Generate PowerPoint presentations from templates (.pptx/.md) or from scratch using MD3 styling. "
        "Tools: list_templates, register_template, discover_layout, generate_deck, render_qa, hardware_diagnostics."
    ),
)


@mcp.tool()
async def list_templates() -> str:
    """List all templates in the persistent template library.

    Returns:
        JSON array of template summaries (id, name, source_type, is_default, layout_count).
    """
    registry = get_template_registry()
    summaries = registry.list_templates()
    return json.dumps([item.model_dump(mode="json") for item in summaries], indent=2)


@mcp.tool()
async def register_template(name: str, template_path: str, is_default: bool = False) -> str:
    """Register a .pptx or .md file in the persistent template library.

    Args:
        name: User-facing template name.
        template_path: Path to the template file on disk.
        is_default: Whether to set this as the default template.

    Returns:
        JSON summary of the registered template including template_id.
    """
    path = Path(template_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {template_path}"})
    registry = get_template_registry()
    try:
        record = registry.register(name, path, is_default=is_default, original_filename=path.name)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    summary = record.summary().model_dump(mode="json")
    summary["template_id"] = record.id
    return json.dumps(summary, indent=2)


@mcp.tool()
async def discover_layout_tool(template_path: str) -> str:
    """Discover slide layouts and placeholders from a .pptx or .md template.

    Args:
        template_path: Absolute or workspace path to the template file.

    Returns:
        JSON layout profile with layout indices and placeholder mappings.
    """
    profile = discover_layout(template_path)
    return profile.model_dump_json(indent=2)


@mcp.tool()
async def generate_deck(
    brief: str,
    template_id: str | None = None,
    template_path: str | None = None,
    mode: str = "scratch",
    title: str | None = None,
    run_qa: bool = True,
) -> str:
    """Generate a presentation from a content brief.

    Args:
        brief: Content brief describing the desired presentation.
        template_id: Optional library template id (preferred over template_path).
        template_path: Optional ad-hoc .pptx or .md template path.
        mode: 'template' or 'scratch'.
        title: Optional deck title.
        run_qa: Whether to run visual QA after generation.

    Returns:
        JSON with output_path, deck_spec, qa_report, and layout_profile.
    """
    request = GenerateRequest(
        brief=brief,
        template_id=template_id,
        template_path=template_path,
        mode=GenerationMode(mode),
        title=title,
        run_qa=run_qa,
    )
    try:
        result = await generate_presentation(request)
    except (ValueError, FileNotFoundError) as exc:
        return json.dumps({"error": str(exc)})
    return result.model_dump_json(indent=2)


@mcp.tool()
async def render_qa(pptx_path: str) -> str:
    """Render a .pptx to slide images and run visual QA.

    Args:
        pptx_path: Path to an existing presentation.

    Returns:
        JSON QA report with passed flag, issues, and slide image paths.
    """
    path = Path(pptx_path)
    if not path.exists():
        return json.dumps({"error": f"File not found: {pptx_path}"})
    report = await run_qa_loop(path)
    return report.model_dump_json(indent=2)


@mcp.tool()
async def hardware_diagnostics() -> str:
    """Return host hardware profile and recommended local models."""
    return json.dumps(run_hardware_diagnostics(), indent=2)


def main() -> None:
    """Run the MCP server with stdio or HTTP transport."""
    parser = argparse.ArgumentParser(description="PPTX Engine MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default=None,
        help="MCP transport (default from MCP_TRANSPORT env or stdio)",
    )
    parser.add_argument("--host", default=None, help="HTTP host")
    parser.add_argument("--port", type=int, default=None, help="HTTP port")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_dirs()
    get_template_registry().seed_builtin_templates()

    transport = args.transport or settings.mcp_transport or "stdio"
    logger.info("Starting MCP server transport={}", transport)

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        host = args.host or settings.api_host
        port = args.port or settings.api_port
        mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()
