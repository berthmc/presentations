"""End-to-end smoke test for scratch compilation."""

from pathlib import Path

import pytest

from presentations.compile.pipeline import compile_deck
from presentations.core.schemas import DeckSpec, GenerationMode, PlaceholderMapping, SlideSpec


@pytest.mark.asyncio
async def test_scratch_compile_smoke(tmp_path: Path) -> None:
    deck = DeckSpec(
        title="Smoke Test Deck",
        mode=GenerationMode.SCRATCH,
        slides=[
            SlideSpec(
                layout_index=0,
                mappings=[
                    PlaceholderMapping(ph_idx=0, content="Smoke Test"),
                    PlaceholderMapping(ph_idx=1, content="Generated locally"),
                ],
            ),
            SlideSpec(
                layout_index=1,
                mappings=[
                    PlaceholderMapping(ph_idx=0, content="Overview"),
                    PlaceholderMapping(
                        ph_idx=1,
                        content="Local-first pipeline\nMD3 styling\nVisual QA loop",
                    ),
                ],
            ),
        ],
    )
    output = tmp_path / "smoke.pptx"
    result = await compile_deck(deck, output)
    assert result.exists()
    assert result.stat().st_size > 1000
