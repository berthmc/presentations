"""Tests for layout role classification and geometry helpers."""

from presentations.core.layout_roles import (
    classify_layout_role,
    detect_column_count,
    detect_media_flags,
    is_text_placeholder,
    summarize_layout,
)
from presentations.core.schemas import LayoutEntry, PlaceholderInfo


def test_classify_agenda_from_name() -> None:
    entry = LayoutEntry(name="Agenda slide", placeholders=[])
    assert classify_layout_role(entry) == "agenda"


def test_classify_two_content_from_geometry() -> None:
    entry = LayoutEntry(
        name="Custom layout",
        placeholders=[
            PlaceholderInfo(index=0, name="Title", type="TITLE (1)", left=0, top=0, width=100, height=50),
            PlaceholderInfo(index=1, name="Left", type="BODY (2)", left=0, top=100, width=400, height=300),
            PlaceholderInfo(index=2, name="Right", type="BODY (2)", left=500, top=100, width=400, height=300),
        ],
    )
    assert classify_layout_role(entry) == "two-content"
    assert detect_column_count(entry) == 2


def test_classify_picture_when_picture_placeholder_present() -> None:
    entry = LayoutEntry(
        name="Content with visual",
        placeholders=[
            PlaceholderInfo(index=0, name="Title", type="TITLE (1)"),
            PlaceholderInfo(index=1, name="Picture", type="PICTURE (18)"),
        ],
    )
    assert classify_layout_role(entry) == "picture"
    has_picture, _, _ = detect_media_flags(entry)
    assert has_picture is True


def test_classify_table_from_name() -> None:
    entry = LayoutEntry(name="Data table layout", placeholders=[])
    assert classify_layout_role(entry) == "table"


def test_summarize_layout_mentions_picture_placeholder() -> None:
    entry = LayoutEntry(
        name="Image and text",
        placeholders=[
            PlaceholderInfo(index=0, name="Title", type="TITLE (1)"),
            PlaceholderInfo(index=1, name="Body", type="BODY (2)"),
            PlaceholderInfo(index=2, name="Picture", type="PICTURE (18)"),
        ],
        has_picture=True,
    )
    summary = summarize_layout(entry)
    assert "picture placeholder" in summary


def test_is_text_placeholder_excludes_picture() -> None:
    assert is_text_placeholder("PICTURE (18)") is False
    assert is_text_placeholder("BODY (2)") is True
