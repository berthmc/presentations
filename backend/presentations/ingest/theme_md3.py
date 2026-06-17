"""Material Design 3 token mapping for presentation themes."""

import re
from pathlib import Path
from typing import Any

from loguru import logger


def _strip_hash(value: str) -> str:
    """Return 6-char hex without leading hash for pptxgenjs compatibility."""
    return value.lstrip("#").upper()[:6]


def _parse_css_vars(css_text: str) -> dict[str, str]:
    """Extract CSS custom properties from a stylesheet."""
    return {
        match.group(1): match.group(2).strip()
        for match in re.finditer(r"--([\w-]+)\s*:\s*([^;]+);", css_text)
    }


def load_md3_theme(brand: str = "tech") -> dict[str, Any]:
    """Load MD3 tokens and map them to a pptxgenjs-friendly palette.

    Args:
        brand: Brand key (`tech` supported; extensible for markets).

    Returns:
        Dictionary with colors, typography, and shape tokens.
    """
    repo_root = Path(__file__).resolve().parents[3]
    token_file = repo_root / "documentation" / "briefs" / "md3-tokens-tech.css"
    if not token_file.exists():
        logger.warning("MD3 token file not found at {}; using built-in defaults", token_file)
        return _default_theme()

    css_vars = _parse_css_vars(token_file.read_text(encoding="utf-8"))
    return {
        "brand": brand,
        "colors": {
            "primary": _strip_hash(css_vars.get("md-sys-color-primary", "3751FF")),
            "onPrimary": _strip_hash(css_vars.get("md-sys-color-on-primary", "FFFFFF")),
            "secondary": _strip_hash(css_vars.get("md-sys-color-secondary", "4F46E5")),
            "tertiary": _strip_hash(css_vars.get("md-sys-color-tertiary", "00B8D4")),
            "surface": _strip_hash(css_vars.get("md-sys-color-surface", "EEF2FF")),
            "onSurface": _strip_hash(css_vars.get("md-sys-color-on-surface", "0F172A")),
            "surfaceContainer": _strip_hash(css_vars.get("md-sys-color-surface-container-lowest", "FFFFFF")),
            "outline": _strip_hash(css_vars.get("md-sys-color-outline-variant", "E2E8F0")),
            "error": _strip_hash(css_vars.get("md-sys-color-error", "DC2626")),
        },
        "typography": {
            "titleFont": "IBM Plex Serif",
            "bodyFont": "Inter",
            "titleSize": 40,
            "sectionSize": 24,
            "bodySize": 16,
            "captionSize": 11,
        },
        "shape": {
            "cornerRadius": css_vars.get("md-sys-shape-corner-md", "16px"),
        },
    }


def _default_theme() -> dict[str, Any]:
    """Fallback MD3 tech theme."""
    return {
        "brand": "tech",
        "colors": {
            "primary": "3751FF",
            "onPrimary": "FFFFFF",
            "secondary": "4F46E5",
            "tertiary": "00B8D4",
            "surface": "EEF2FF",
            "onSurface": "0F172A",
            "surfaceContainer": "FFFFFF",
            "outline": "E2E8F0",
            "error": "DC2626",
        },
        "typography": {
            "titleFont": "IBM Plex Serif",
            "bodyFont": "Inter",
            "titleSize": 40,
            "sectionSize": 24,
            "bodySize": 16,
            "captionSize": 11,
        },
        "shape": {"cornerRadius": "16px"},
    }


def theme_to_pptxgenjs_config(theme: dict[str, Any]) -> dict[str, Any]:
    """Convert theme dict to pptxgenjs builder input."""
    colors = theme.get("colors", {})
    typography = theme.get("typography", {})
    return {
        "layout": "LAYOUT_16x9",
        "colors": colors,
        "fonts": typography,
    }
