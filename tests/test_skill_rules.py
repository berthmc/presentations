"""Tests for skill_rules formatting and compliance helpers."""

from presentations.agents.skill_rules import (
    check_leftover_placeholder_text,
    check_unicode_bullets,
    estimate_text_overflow,
    normalize_content_lines,
)


def test_normalize_content_lines_strips_unicode_bullets() -> None:
    lines = normalize_content_lines("• First item\n- Second item")
    assert lines == ["First item", "Second item"]


def test_check_leftover_placeholder_text_detects_lorem() -> None:
    issues = check_leftover_placeholder_text("Lorem ipsum dolor sit amet")
    assert issues


def test_check_unicode_bullets_flags_bullet_char() -> None:
    issues = check_unicode_bullets("• Item one")
    assert issues


def test_estimate_text_overflow_flags_long_content() -> None:
    text = "word " * 500
    result = estimate_text_overflow(text, width_emu=914400, height_emu=457200, font_size_pt=14.0)
    assert result["overflow"] is True
    assert result["overflow_lines"] > 0
