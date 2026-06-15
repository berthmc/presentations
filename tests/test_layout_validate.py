"""Tests for deck layout validation and sanitization."""

import pytest

from presentations.core.schemas import (
    DeckSpec,
    GenerationMode,
    LayoutEntry,
    LayoutProfile,
    PlaceholderInfo,
    PlaceholderMapping,
    SlideSpec,
)
from presentations.llm.layout_validate import (
    layout_validation_errors,
    sanitize_deck_spec,
    validate_deck_against_layout,
)

LAYOUT = LayoutProfile(
    source_path="/tmp/template.pptx",
    source_type="pptx",
    layouts={
        1: LayoutEntry(
            name="Title",
            placeholders=[
                PlaceholderInfo(index=0, name="title", type="TITLE"),
                PlaceholderInfo(index=10, name="subtitle", type="BODY"),
            ],
        ),
        14: LayoutEntry(
            name="Content",
            placeholders=[
                PlaceholderInfo(index=0, name="heading", type="TITLE"),
                PlaceholderInfo(index=11, name="body", type="BODY"),
            ],
        ),
    },
)


def test_layout_validation_errors_detects_invalid_ph_idx() -> None:
    deck = DeckSpec(
        title="Test",
        mode=GenerationMode.TEMPLATE,
        slides=[
            SlideSpec(
                layout_index=1,
                mappings=[
                    PlaceholderMapping(ph_idx=1, content="Bad"),
                    PlaceholderMapping(ph_idx=4, content="Also bad"),
                ],
            )
        ],
    )
    errors = layout_validation_errors(deck, LAYOUT)
    assert len(errors) == 1
    assert "ph_idx [1, 4]" in errors[0]
    assert "Allowed ph_idx" in errors[0]


def test_validate_deck_against_layout_raises() -> None:
    deck = DeckSpec(
        title="Test",
        mode=GenerationMode.TEMPLATE,
        slides=[SlideSpec(layout_index=99, mappings=[])],
    )
    with pytest.raises(ValueError, match="layout_index 99"):
        validate_deck_against_layout(deck, LAYOUT)


def test_sanitize_deck_spec_remaps_orphan_content() -> None:
    deck = DeckSpec(
        title="Test",
        mode=GenerationMode.TEMPLATE,
        slides=[
            SlideSpec(
                layout_index=14,
                mappings=[
                    PlaceholderMapping(ph_idx=2, content="Orphan A"),
                    PlaceholderMapping(ph_idx=4, content="Orphan B"),
                ],
            )
        ],
    )
    sanitized = sanitize_deck_spec(deck, LAYOUT)
    assert sanitized.slides[0].layout_index == 14
    assert len(sanitized.slides[0].mappings) == 1
    assert sanitized.slides[0].mappings[0].ph_idx == 0
    assert "Orphan A" in sanitized.slides[0].mappings[0].content
    assert "Orphan B" in sanitized.slides[0].mappings[0].content


def test_sanitize_deck_spec_keeps_valid_mappings() -> None:
    deck = DeckSpec(
        title="Test",
        mode=GenerationMode.TEMPLATE,
        slides=[
            SlideSpec(
                layout_index=1,
                mappings=[
                    PlaceholderMapping(ph_idx=0, content="Title"),
                    PlaceholderMapping(ph_idx=10, content="Subtitle"),
                ],
            )
        ],
    )
    sanitized = sanitize_deck_spec(deck, LAYOUT)
    assert len(sanitized.slides[0].mappings) == 2
    assert sanitized.slides[0].mappings[0].ph_idx == 0
