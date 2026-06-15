"""Layout discovery tests."""

from pathlib import Path

from presentations.ingest.discover import discover_layout


def test_discover_md_template() -> None:
    profile = discover_layout(Path("templates/sample-deck.md"))
    assert profile.source_type == "md"
    assert 0 in profile.layouts
