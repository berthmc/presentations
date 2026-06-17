"""Parse markdown-based presentation templates."""

import re
from pathlib import Path

import yaml

from presentations.core.schemas import LayoutEntry, LayoutProfile, PlaceholderInfo
from presentations.ingest.theme_md3 import load_md3_theme

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SLIDE_RE = re.compile(r"^##\s+slide:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"^\s*-\s*(?:ph_idx|placeholder)\s*:\s*(\d+)\s*(?:\|\s*(.+))?$", re.MULTILINE)


def parse_md_template(template_path: str | Path) -> LayoutProfile:
    """Parse a markdown template into a LayoutProfile.

    Expected format::

        ---
        theme: tech
        title: Corporate Deck
        ---

        ## slide: Title Slide
        - ph_idx: 0 | title
        - ph_idx: 1 | subtitle

    Args:
        template_path: Path to the .md template file.

    Returns:
        LayoutProfile describing slide layouts and MD3 theme tokens.
    """
    path = Path(template_path)
    text = path.read_text(encoding="utf-8")
    theme_name = "tech"
    match = _FRONT_MATTER_RE.match(text)
    body = text
    if match:
        front_matter = yaml.safe_load(match.group(1)) or {}
        theme_name = front_matter.get("theme", "tech")
        body = text[match.end() :]

    theme = load_md3_theme(theme_name)
    layouts: dict[int, LayoutEntry] = {}
    slide_blocks = _SLIDE_RE.split(body)
    # split returns [preamble, name1, block1, name2, block2, ...]
    layout_index = 0
    for index in range(1, len(slide_blocks), 2):
        layout_name = slide_blocks[index].strip()
        block = slide_blocks[index + 1] if index + 1 < len(slide_blocks) else ""
        placeholders: list[PlaceholderInfo] = []
        for ph_match in _PLACEHOLDER_RE.finditer(block):
            ph_idx = int(ph_match.group(1))
            label = (ph_match.group(2) or f"placeholder_{ph_idx}").strip()
            placeholders.append(PlaceholderInfo(index=ph_idx, name=label, type="BODY"))
        layouts[layout_index] = LayoutEntry(name=layout_name, placeholders=placeholders)
        layout_index += 1

    if not layouts:
        layouts[0] = LayoutEntry(
            name="Default",
            placeholders=[
                PlaceholderInfo(index=0, name="title", type="TITLE"),
                PlaceholderInfo(index=1, name="body", type="BODY"),
            ],
        )

    return LayoutProfile(
        source_path=str(path.resolve()),
        source_type="md",
        layouts=layouts,
        theme=theme,
    )
