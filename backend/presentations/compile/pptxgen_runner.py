"""Invoke the Node pptxgenjs builder subprocess."""

import asyncio
import json
from pathlib import Path

from loguru import logger

from presentations.core.schemas import DeckSpec
from presentations.ingest.theme_md3 import load_md3_theme, theme_to_pptxgenjs_config


def _builder_path() -> Path:
    return Path(__file__).resolve().parent / "node" / "builder.mjs"


async def compile_from_scratch(deck_spec: DeckSpec, output_path: str | Path, theme_name: str = "tech") -> Path:
    """Build a presentation from scratch using pptxgenjs.

    Args:
        deck_spec: Structured slide content.
        output_path: Destination .pptx path.
        theme_name: MD3 brand key.

    Returns:
        Path to generated presentation.
    """
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    theme = theme_to_pptxgenjs_config(load_md3_theme(theme_name))
    payload = {
        "deckSpec": deck_spec.model_dump(),
        "theme": theme,
        "outputPath": str(destination.resolve()),
    }

    builder = _builder_path()
    node_dir = builder.parent
    proc = await asyncio.create_subprocess_exec(
        "node",
        str(builder),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(node_dir),
    )
    stdout, stderr = await proc.communicate(json.dumps(payload).encode("utf-8"))
    if proc.returncode != 0:
        logger.error("pptxgenjs builder failed: {}", stderr.decode("utf-8", errors="replace"))
        raise RuntimeError(f"pptxgenjs builder failed: {stderr.decode('utf-8', errors='replace')}")

    logger.info("Compiled scratch deck to {}", destination)
    return destination
