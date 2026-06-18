"""Extract and rotate theme accent colours from a .pptx template."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger
from pptx import Presentation
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_xml

_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_ACCENT_TAGS = ("accent1", "accent2", "accent3", "accent4", "accent5", "accent6")
_SCHEME_COLOR_TAGS = ("dk1", "lt1", "dk2", "lt2")
_ACCENT_ENUMS = (
    MSO_THEME_COLOR.ACCENT_1,
    MSO_THEME_COLOR.ACCENT_2,
    MSO_THEME_COLOR.ACCENT_3,
    MSO_THEME_COLOR.ACCENT_4,
    MSO_THEME_COLOR.ACCENT_5,
    MSO_THEME_COLOR.ACCENT_6,
)
_DEFAULT_ROTATION = (
    MSO_THEME_COLOR.ACCENT_1,
    MSO_THEME_COLOR.ACCENT_3,
    MSO_THEME_COLOR.ACCENT_4,
    MSO_THEME_COLOR.ACCENT_6,
    MSO_THEME_COLOR.ACCENT_2,
)
_MIN_CONTRAST_ON_WHITE = 3.0


def relative_luminance(hex_color: str) -> float:
    """Return WCAG relative luminance for a six-digit sRGB hex colour."""
    red = int(hex_color[0:2], 16) / 255
    green = int(hex_color[2:4], 16) / 255
    blue = int(hex_color[4:6], 16) / 255

    def linearize(channel: float) -> float:
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red_l = linearize(red)
    green_l = linearize(green)
    blue_l = linearize(blue)
    return 0.2126 * red_l + 0.7152 * green_l + 0.0722 * blue_l


def contrast_on_white(hex_color: str) -> float:
    """Return contrast ratio between a colour and white."""
    luminance = relative_luminance(hex_color)
    lighter = 1.0
    darker = luminance
    return (lighter + 0.05) / (darker + 0.05)


def _hex_from_color_element(color_element) -> str | None:
    """Read an sRGB or sysClr lastClr value from a theme colour element."""
    srgb = color_element.find(f"{{{_DRAWING_NS}}}srgbClr")
    if srgb is not None:
        value = srgb.get("val")
        if value:
            return value.upper()
    sys_clr = color_element.find(f"{{{_DRAWING_NS}}}sysClr")
    if sys_clr is not None:
        value = sys_clr.get("lastClr")
        if value:
            return value.upper()
    return None


def _read_theme_element(prs: Presentation):
    """Return the parsed theme XML element or None."""
    try:
        theme_part = prs.slide_masters[0].part.part_related_by(RT.THEME)
    except KeyError:
        logger.debug("No theme part on slide master; using default accent rotation")
        return None
    return parse_xml(theme_part.blob)


def _font_from_scheme(font_scheme_element, tag: str) -> str:
    """Read the latin typeface from a majorFont or minorFont element."""
    if font_scheme_element is None:
        return ""
    font_element = font_scheme_element.find(f"{{{_DRAWING_NS}}}{tag}")
    if font_element is None:
        return ""
    latin = font_element.find(f"{{{_DRAWING_NS}}}latin")
    if latin is None:
        return ""
    return latin.get("typeface") or ""


def extract_theme_metadata(prs: Presentation) -> dict[str, Any]:
    """Return accent colours, base colours, and font scheme from a template."""
    theme: dict[str, Any] = {
        "accents": {},
        "colors": {},
        "fonts": {"major": "", "minor": ""},
    }
    theme_element = _read_theme_element(prs)
    if theme_element is None:
        return theme

    clr_scheme = theme_element.find(f".//{{{_DRAWING_NS}}}clrScheme")
    if clr_scheme is not None:
        for tag in _SCHEME_COLOR_TAGS:
            color_element = clr_scheme.find(f"{{{_DRAWING_NS}}}{tag}")
            if color_element is None:
                continue
            hex_color = _hex_from_color_element(color_element)
            if hex_color:
                theme["colors"][tag] = hex_color
        for tag in _ACCENT_TAGS:
            color_element = clr_scheme.find(f"{{{_DRAWING_NS}}}{tag}")
            if color_element is None:
                continue
            hex_color = _hex_from_color_element(color_element)
            if hex_color:
                theme["accents"][tag] = hex_color

    font_scheme = theme_element.find(f".//{{{_DRAWING_NS}}}fontScheme")
    if font_scheme is not None:
        theme["fonts"]["major"] = _font_from_scheme(font_scheme, "majorFont")
        theme["fonts"]["minor"] = _font_from_scheme(font_scheme, "minorFont")

    return theme


def extract_theme_accent_hex(prs: Presentation) -> dict[MSO_THEME_COLOR, str]:
    """Return accent theme colours mapped to six-digit hex values."""
    accents: dict[MSO_THEME_COLOR, str] = {}
    theme_element = _read_theme_element(prs)
    if theme_element is None:
        return accents

    clr_scheme = theme_element.find(f".//{{{_DRAWING_NS}}}clrScheme")
    if clr_scheme is None:
        return accents

    for tag, enum in zip(_ACCENT_TAGS, _ACCENT_ENUMS, strict=True):
        color_element = clr_scheme.find(f"{{{_DRAWING_NS}}}{tag}")
        if color_element is None:
            continue
        hex_color = _hex_from_color_element(color_element)
        if hex_color:
            accents[enum] = hex_color
    return accents


def usable_accent_colors(
    accent_hex: dict[MSO_THEME_COLOR, str],
    *,
    min_contrast: float = _MIN_CONTRAST_ON_WHITE,
) -> list[MSO_THEME_COLOR]:
    """Return accent colours with sufficient contrast on a white background."""
    preferred = [accent for accent in _DEFAULT_ROTATION if accent in accent_hex]
    usable = [
        accent
        for accent in preferred
        if contrast_on_white(accent_hex[accent]) >= min_contrast
    ]
    if usable:
        return usable

    fallback = [
        accent
        for accent in _ACCENT_ENUMS
        if accent in accent_hex and contrast_on_white(accent_hex[accent]) >= min_contrast
    ]
    return fallback or list(_DEFAULT_ROTATION)


@dataclass(frozen=True)
class ThemePalette:
    """Rotating palette of theme accent colours extracted from a template."""

    accents: tuple[MSO_THEME_COLOR, ...]

    def accent_for_slide(self, slide_num: int) -> MSO_THEME_COLOR:
        """Return the accent colour for a one-based slide number."""
        if not self.accents:
            return MSO_THEME_COLOR.ACCENT_1
        return self.accents[(slide_num - 1) % len(self.accents)]


def build_theme_palette(prs: Presentation) -> ThemePalette:
    """Build a contrast-safe accent rotation from the presentation theme."""
    accent_hex = extract_theme_accent_hex(prs)
    accents = usable_accent_colors(accent_hex)
    logger.debug("Theme palette usable accents={}", [accent.name for accent in accents])
    return ThemePalette(accents=tuple(accents))
