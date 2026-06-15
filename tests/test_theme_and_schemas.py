"""Theme and schema tests."""

from pathlib import Path

from presentations.core.schemas import DeckSpec, GenerationMode, PlaceholderMapping, SlideSpec
from presentations.ingest.md_template import parse_md_template
from presentations.ingest.theme_md3 import load_md3_theme, theme_to_pptxgenjs_config


def test_load_md3_theme_has_required_colors() -> None:
    theme = load_md3_theme("tech")
    colors = theme["colors"]
    assert "primary" in colors
    assert not colors["primary"].startswith("#")
    assert len(colors["primary"]) == 6


def test_theme_to_pptxgenjs_config() -> None:
    theme = load_md3_theme("tech")
    config = theme_to_pptxgenjs_config(theme)
    assert config["layout"] == "LAYOUT_16x9"
    assert "colors" in config


def test_parse_md_template() -> None:
    template = Path("templates/sample-deck.md")
    profile = parse_md_template(template)
    assert profile.source_type == "md"
    assert len(profile.layouts) >= 3
    assert profile.layouts[0].placeholders[0].name == "title"


def test_deck_spec_validation() -> None:
    deck = DeckSpec(
        title="Test",
        mode=GenerationMode.SCRATCH,
        slides=[
            SlideSpec(
                layout_index=0,
                mappings=[PlaceholderMapping(ph_idx=0, content="Hello")],
            )
        ],
    )
    assert deck.slides[0].mappings[0].content == "Hello"
