"""Unified compile entrypoint."""

from pathlib import Path

from loguru import logger

from presentations.compile.pptx_template import compile_from_template
from presentations.compile.pptxgen_runner import compile_from_scratch
from presentations.core.schemas import DeckSpec, GenerationMode, LayoutProfile


async def compile_deck(
    deck_spec: DeckSpec,
    output_path: str | Path,
    template_path: str | Path | None = None,
    layout_profile: LayoutProfile | None = None,
) -> Path:
    """Compile a deck using template or scratch path.

    Args:
        deck_spec: Structured slide specification.
        output_path: Output .pptx path.
        template_path: Template file for template mode.
        layout_profile: Optional layout metadata.

    Returns:
        Path to generated file.
    """
    mode = deck_spec.mode
    if mode == GenerationMode.TEMPLATE:
        if not template_path:
            raise ValueError("template_path is required for template mode")
        return compile_from_template(template_path, deck_spec, output_path, layout_profile)

    theme_name = "tech"
    if layout_profile and layout_profile.theme:
        theme_name = layout_profile.theme.get("brand", "tech")
    logger.info("Compiling scratch deck with MD3 theme {}", theme_name)
    return await compile_from_scratch(deck_spec, output_path, theme_name=theme_name)
