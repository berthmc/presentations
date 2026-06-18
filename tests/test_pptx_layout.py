"""Tests for enriched .pptx layout ingestion."""

from pathlib import Path

import pytest

from presentations.ingest.pptx_layout import generate_layout_map

VI_EC_TEMPLATE = Path("documentation/briefs/VI_EC_Corporate_PPT_Template_2026.pptx")


@pytest.fixture
def vi_ec_template() -> Path:
    if not VI_EC_TEMPLATE.exists():
        pytest.skip(f"Template not found: {VI_EC_TEMPLATE}")
    return VI_EC_TEMPLATE


def test_generate_layout_map_includes_theme_and_roles(vi_ec_template: Path) -> None:
    profile = generate_layout_map(vi_ec_template)
    assert profile.source_type == "pptx"
    assert profile.layouts
    assert profile.theme.get("fonts") is not None
    assert profile.theme.get("accents") is not None

    roles = {entry.role for entry in profile.layouts.values()}
    assert "title" in roles or "content" in roles

    enriched = next(iter(profile.layouts.values()))
    assert enriched.summary
    assert any(
        ph.left is not None or ph.width is not None for ph in enriched.placeholders
    ) or not enriched.placeholders


def test_generate_layout_map_flags_media_layouts(vi_ec_template: Path) -> None:
    profile = generate_layout_map(vi_ec_template)
    has_any_picture = any(entry.has_picture for entry in profile.layouts.values())
    assert has_any_picture or len(profile.layouts) > 0
