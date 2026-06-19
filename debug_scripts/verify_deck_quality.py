"""Verify deck-quality sanitization against the investor deck pattern."""

from __future__ import annotations

import sys
from pathlib import Path

from presentations.agents.assembler import compile_from_template
from presentations.core.schemas import DeckSpec, GenerationMode, PlaceholderMapping, SlideSpec
from presentations.ingest.pptx_layout import generate_layout_map
from presentations.llm.layout_validate import sanitize_deck_spec

TEMPLATE_GLOB = "documentation/briefs/*7199cd57.pptx"
OUTPUT = Path("debug_scripts/deck_quality_verify.pptx")


def _first_layout(profile, role: str) -> int:
    for idx, entry in sorted(profile.layouts.items()):
        if entry.role == role:
            return idx
    raise ValueError(f"No layout with role {role}")


def main() -> int:
    matches = list(Path(".").glob(TEMPLATE_GLOB))
    if not matches:
        print("Generated deck fixture not found", file=sys.stderr)
        return 1

    profile = generate_layout_map(matches[0])
    title_idx = _first_layout(profile, "title")
    content_idx = _first_layout(profile, "content")
    two_col_idx = _first_layout(profile, "two-content")
    section_idx = _first_layout(profile, "section")

    deck = DeckSpec(
        title="MiFID II: Protecting EU Retail Investors",
        mode=GenerationMode.TEMPLATE,
        slides=[
            SlideSpec(
                layout_index=title_idx,
                mappings=[
                    PlaceholderMapping(ph_idx=0, content="Title Slide"),
                    PlaceholderMapping(ph_idx=10, content="Transparency, Best execution"),
                ],
            ),
            SlideSpec(
                layout_index=content_idx,
                mappings=[PlaceholderMapping(ph_idx=0, content="Overview")],
            ),
            SlideSpec(
                layout_index=two_col_idx,
                mappings=[
                    PlaceholderMapping(ph_idx=0, content="Best Execution"),
                    PlaceholderMapping(
                        ph_idx=1,
                        content="Left obligation\nRight obligation\nExtra left\nExtra right",
                    ),
                ],
            ),
            SlideSpec(
                layout_index=section_idx,
                mappings=[
                    PlaceholderMapping(ph_idx=0, content="Product Governance"),
                    PlaceholderMapping(
                        ph_idx=11,
                        content="Long lifecycle management content that should move off the divider layout.",
                    ),
                ],
            ),
            SlideSpec(
                layout_index=section_idx,
                mappings=[PlaceholderMapping(ph_idx=0, content="Thank you")],
            ),
        ],
    )

    sanitized = sanitize_deck_spec(deck, profile)
    slide1_title = next(m.content for m in sanitized.slides[0].mappings if m.ph_idx == 0)
    two_col_bodies = {m.ph_idx for m in sanitized.slides[2].mappings if m.ph_idx != 0}
    interior_layout = sanitized.slides[3].layout_index

    print(f"slide1_title={slide1_title!r}")
    print(f"two_col_body_ph={sorted(two_col_bodies)}")
    print(f"interior_slide_layout={interior_layout} role={profile.layouts[interior_layout].role}")

    if slide1_title != deck.title:
        print("FAIL: title artifact not fixed", file=sys.stderr)
        return 1
    if len(two_col_bodies) < 2:
        print("FAIL: multi-column not distributed", file=sys.stderr)
        return 1
    if profile.layouts[interior_layout].role == "section":
        print("FAIL: interior body still on section layout", file=sys.stderr)
        return 1

    compile_from_template(matches[0], sanitized, OUTPUT, profile)
    print(f"OK compiled to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
