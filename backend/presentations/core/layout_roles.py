"""Classify slide layout roles for synthesis prompts and structural enforcement."""

from __future__ import annotations

from presentations.core.schemas import LayoutEntry, LayoutProfile, PlaceholderMapping, SlideSpec


def classify_layout_role(entry: LayoutEntry) -> str:
    """Infer a layout role from placeholder metadata and layout name."""
    name = entry.name.lower()
    placeholder_types = {ph.type.upper() for ph in entry.placeholders}
    placeholder_count = len(entry.placeholders)

    if any(keyword in name for keyword in ("section", "divider", "break", "chapter")):
        return "section"
    if any(keyword in name for keyword in ("closing", "thank", "end slide", "goodbye")):
        return "closing"
    if any(keyword in name for keyword in ("cover page", "title slide")) or (
        "cover" in name and "page" in name
    ):
        return "title"
    if ("two" in name and "content" in name) or "comparison" in name or "compare" in name:
        return "two-content"
    if "blank" in name:
        return "blank"

    has_title = any("TITLE" in ph_type for ph_type in placeholder_types)
    has_body = any("BODY" in ph_type or "OBJECT" in ph_type for ph_type in placeholder_types)

    if has_title and not has_body and placeholder_count <= 2:
        return "title"
    if "title slide" in name or (name.strip() == "title"):
        return "title"
    if "title and content" in name or (has_title and has_body):
        return "content"
    return "content"


def classify_layout_role_from_name(name: str) -> str:
    """Classify a layout role when only the layout name is available."""
    return classify_layout_role(LayoutEntry(name=name, placeholders=[]))


def _remap_slide_to_layout(slide: SlideSpec, new_layout_index: int, layout: LayoutProfile) -> SlideSpec:
    """Remap slide placeholder mappings onto a different layout."""
    entry = layout.layouts[new_layout_index]
    if not entry.placeholders:
        return SlideSpec(layout_index=new_layout_index, mappings=[], notes=slide.notes)

    title_ph = next(
        (ph for ph in entry.placeholders if "TITLE" in ph.type.upper()),
        entry.placeholders[0],
    )
    body_ph = next(
        (ph for ph in entry.placeholders if ph.index != title_ph.index),
        title_ph,
    )

    merged: dict[int, list[str]] = {}
    for index, mapping in enumerate(slide.mappings):
        target = title_ph if index == 0 else body_ph
        merged.setdefault(target.index, []).append(mapping.content)

    mappings = [
        PlaceholderMapping(ph_idx=ph_idx, content="\n".join(parts))
        for ph_idx, parts in merged.items()
        if any(part.strip() for part in parts)
    ]
    return SlideSpec(layout_index=new_layout_index, mappings=mappings, notes=slide.notes)


def enforce_structural_layouts(deck, layout: LayoutProfile):
    """Force opening and closing slides onto title/closing layouts when available."""
    from presentations.core.schemas import DeckSpec

    if not isinstance(deck, DeckSpec):
        raise TypeError("enforce_structural_layouts expects a DeckSpec")

    if not layout.layouts or not deck.slides:
        return deck

    roles = {index: classify_layout_role(entry) for index, entry in layout.layouts.items()}
    title_layouts = sorted(index for index, role in roles.items() if role == "title")
    closing_layouts = sorted(
        index for index, role in roles.items() if role in {"closing", "section"}
    )

    slides = list(deck.slides)
    changed = False

    if len(slides) > 1 and title_layouts and slides[0].layout_index not in title_layouts:
        slides[0] = _remap_slide_to_layout(slides[0], title_layouts[0], layout)
        changed = True

    if len(slides) > 1 and closing_layouts and slides[-1].layout_index not in closing_layouts:
        slides[-1] = _remap_slide_to_layout(slides[-1], closing_layouts[-1], layout)
        changed = True

    if changed:
        return deck.model_copy(update={"slides": slides})
    return deck
