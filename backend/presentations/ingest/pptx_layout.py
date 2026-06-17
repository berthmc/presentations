"""Extract layout profiles from .pptx templates."""

from pathlib import Path

from pptx import Presentation

from presentations.core.schemas import LayoutEntry, LayoutProfile, PlaceholderInfo


def generate_layout_map(template_path: str | Path) -> LayoutProfile:
    """Analyze master slides in a target presentation template and return a mapping profile.

    Args:
        template_path: Path to the corporate .pptx template.

    Returns:
        LayoutProfile with layout indices and placeholder metadata.
    """
    path = Path(template_path)
    prs = Presentation(str(path))
    layout_profile: dict[int, LayoutEntry] = {}

    for idx, layout in enumerate(prs.slide_layouts):
        placeholders = [
            PlaceholderInfo(
                index=ph.placeholder_format.idx,
                name=ph.name,
                type=str(ph.placeholder_format.type),
            )
            for ph in layout.placeholders
        ]
        layout_profile[idx] = LayoutEntry(name=layout.name, placeholders=placeholders)

    return LayoutProfile(source_path=str(path.resolve()), source_type="pptx", layouts=layout_profile)
