"""Discover layout profiles from pptx or markdown templates."""

from pathlib import Path

from presentations.core.schemas import LayoutProfile
from presentations.ingest.md_template import parse_md_template
from presentations.ingest.pptx_layout import generate_layout_map


def discover_layout(template_path: str | Path) -> LayoutProfile:
    """Discover layout metadata from a template file.

    Args:
        template_path: Path to `.pptx` or `.md` template.

    Returns:
        LayoutProfile for the template.

    Raises:
        ValueError: If the file extension is unsupported.
    """
    path = Path(template_path)
    suffix = path.suffix.lower()
    if suffix == ".pptx":
        return generate_layout_map(path)
    if suffix == ".md":
        return parse_md_template(path)
    raise ValueError(f"Unsupported template type: {suffix}")
