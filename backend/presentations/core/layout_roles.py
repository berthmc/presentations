"""Classify slide layout roles for synthesis prompts and structural enforcement."""

from __future__ import annotations

from presentations.core.schemas import (
    LayoutEntry,
    LayoutProfile,
    PlaceholderInfo,
    PlaceholderMapping,
    SlideSpec,
)

_TEXT_PLACEHOLDER_KEYWORDS = ("TITLE", "BODY", "CONTENT", "CENTER", "SUBTITLE", "FOOTER")
_GRAPHIC_PLACEHOLDER_KEYWORDS = ("PICTURE", "CHART", "TABLE", "OBJECT", "MEDIA", "CLIP")


def _placeholder_types(entry: LayoutEntry) -> set[str]:
    """Return upper-case placeholder type strings for a layout."""
    return {ph.type.upper() for ph in entry.placeholders}


def _name_has_any(name: str, keywords: tuple[str, ...]) -> bool:
    """Return True when any keyword appears in the layout name."""
    lowered = name.lower()
    return any(keyword in lowered for keyword in keywords)


def _has_placeholder_type(entry: LayoutEntry, *keywords: str) -> bool:
    """Return True when any placeholder type contains a keyword."""
    types = _placeholder_types(entry)
    return any(keyword in ph_type for ph_type in types for keyword in keywords)


def body_placeholders(entry: LayoutEntry) -> list[PlaceholderInfo]:
    """Return non-title body placeholders sorted by horizontal position."""
    bodies: list[PlaceholderInfo] = []
    for ph in entry.placeholders:
        ph_type = ph.type.upper()
        if any(keyword in ph_type for keyword in ("TITLE", "SLIDE_NUMBER", "FOOTER", "DATE", "HEADER")):
            continue
        if any(keyword in ph_type for keyword in ("BODY", "CONTENT", "OBJECT", "CENTER")):
            bodies.append(ph)
    bodies.sort(key=lambda placeholder: (placeholder.left or 0, placeholder.index))
    return bodies


def title_placeholder(entry: LayoutEntry) -> PlaceholderInfo | None:
    """Return the primary title placeholder for a layout, if any."""
    for ph in entry.placeholders:
        if "TITLE" in ph.type.upper():
            return ph
    return None


def slide_body_char_count(slide: SlideSpec, entry: LayoutEntry) -> int:
    """Return total character count mapped to body placeholders on a slide."""
    body_indices = {ph.index for ph in body_placeholders(entry)}
    return sum(len(mapping.content) for mapping in slide.mappings if mapping.ph_idx in body_indices)


def remap_content_off_dividers(deck, layout: LayoutProfile, *, char_threshold: int = 60):
    """Remap interior slides with substantive body content off section/divider layouts."""
    from presentations.core.schemas import DeckSpec

    if not isinstance(deck, DeckSpec):
        raise TypeError("remap_content_off_dividers expects a DeckSpec")

    if len(deck.slides) <= 2 or not layout.layouts:
        return deck

    content_layouts = sorted(
        index
        for index, entry in layout.layouts.items()
        if layout_role_for_entry(entry) == "content"
    )
    if not content_layouts:
        return deck

    target_layout = content_layouts[0]
    slides = list(deck.slides)
    changed = False

    for index in range(1, len(slides) - 1):
        slide = slides[index]
        entry = layout.layouts.get(slide.layout_index)
        if entry is None:
            continue
        role = layout_role_for_entry(entry)
        if role not in {"section", "blank"}:
            continue
        if slide_body_char_count(slide, entry) <= char_threshold:
            continue
        slides[index] = _remap_slide_to_layout(slide, target_layout, layout)
        changed = True

    if changed:
        return deck.model_copy(update={"slides": slides})
    return deck


def _content_placeholders(entry: LayoutEntry) -> list[PlaceholderInfo]:
    """Return placeholders that typically hold text content."""
    content: list[PlaceholderInfo] = []
    for ph in entry.placeholders:
        ph_type = ph.type.upper()
        if any(keyword in ph_type for keyword in _TEXT_PLACEHOLDER_KEYWORDS):
            content.append(ph)
        elif "OBJECT" in ph_type and "PICTURE" not in ph_type and "CHART" not in ph_type:
            content.append(ph)
    return content


def detect_column_count(entry: LayoutEntry) -> int:
    """Count side-by-side content columns from placeholder geometry."""
    bodies = [
        ph
        for ph in _content_placeholders(entry)
        if ph.left is not None and ph.width is not None and "TITLE" not in ph.type.upper()
    ]
    if len(bodies) < 2:
        return 1

    bodies.sort(key=lambda ph: ph.left or 0)
    columns = 1
    overlap_tolerance_emu = 100_000
    for index in range(1, len(bodies)):
        previous = bodies[index - 1]
        current = bodies[index]
        previous_right = (previous.left or 0) + (previous.width or 0)
        if (current.left or 0) >= previous_right - overlap_tolerance_emu:
            columns += 1
    return min(columns, 3)


def detect_media_flags(entry: LayoutEntry) -> tuple[bool, bool, bool]:
    """Return has_picture, has_chart, has_table for a layout."""
    return _detect_media_flags(entry)


def _detect_media_flags(entry: LayoutEntry) -> tuple[bool, bool, bool]:
    """Return has_picture, has_chart, has_table for a layout."""
    has_picture = _has_placeholder_type(entry, "PICTURE") or _name_has_any(
        entry.name, ("picture", "image", "photo", "visual")
    )
    has_chart = _has_placeholder_type(entry, "CHART") or _name_has_any(
        entry.name, ("chart", "graph", "data", "metric", "kpi")
    )
    has_table = _has_placeholder_type(entry, "TABLE") or _name_has_any(entry.name, ("table", "grid"))
    return has_picture, has_chart, has_table


def classify_layout_role(entry: LayoutEntry) -> str:
    """Infer a layout role from placeholder metadata, geometry, and layout name."""
    name = entry.name.lower()
    placeholder_types = _placeholder_types(entry)
    placeholder_count = len(entry.placeholders)
    has_picture, has_chart, has_table = _detect_media_flags(entry)
    columns = detect_column_count(entry)

    if _name_has_any(name, ("section", "divider", "break", "chapter")):
        return "section"
    if _name_has_any(name, ("closing", "thank", "end slide", "goodbye")):
        return "closing"
    if _name_has_any(name, ("cover page", "title slide")) or ("cover" in name and "page" in name):
        return "title"
    if _name_has_any(name, ("agenda", "table of contents", "outline", "contents")):
        return "agenda"
    if _name_has_any(name, ("quote", "testimonial", "callout")):
        return "quote"
    if _name_has_any(name, ("team", "people", "org chart", "organisation")):
        return "team"
    if _name_has_any(name, ("timeline", "process", "roadmap", "journey")):
        return "timeline"
    if "blank" in name:
        return "blank"
    if has_table:
        return "table"
    if has_chart:
        return "chart"
    if has_picture and not any("BODY" in ph_type or "CONTENT" in ph_type for ph_type in placeholder_types):
        return "picture"
    if ("two" in name and "content" in name) or "comparison" in name or "compare" in name:
        return "two-content"
    if columns >= 2:
        return "two-content"
    if has_picture:
        return "picture"

    has_title = any("TITLE" in ph_type for ph_type in placeholder_types)
    has_body = any("BODY" in ph_type or "OBJECT" in ph_type or "CONTENT" in ph_type for ph_type in placeholder_types)

    if has_title and not has_body and placeholder_count <= 2:
        return "title"
    if "title slide" in name or name.strip() == "title":
        return "title"
    if "title and content" in name or (has_title and has_body):
        return "content"
    return "content"


def summarize_layout(entry: LayoutEntry) -> str:
    """Build a short natural-language summary of a layout for LLM prompts."""
    role = classify_layout_role(entry)
    has_picture, has_chart, has_table = _detect_media_flags(entry)
    columns = detect_column_count(entry)
    parts: list[str] = [f"Role: {role}."]

    if columns >= 2:
        parts.append(f"{columns}-column layout for comparisons or paired concepts.")
    elif role == "content":
        parts.append("Standard title plus body content.")
    elif role == "section":
        parts.append("Section divider with prominent heading.")
    elif role == "title":
        parts.append("Opening or cover slide.")
    elif role == "closing":
        parts.append("Closing or thank-you slide.")
    elif role == "agenda":
        parts.append("Agenda or table-of-contents slide.")
    elif role == "quote":
        parts.append("Quote or callout slide.")
    elif role == "team":
        parts.append("Team or people slide.")
    elif role == "timeline":
        parts.append("Timeline or process slide.")

    media_bits: list[str] = []
    if has_picture:
        media_bits.append("picture placeholder (template imagery preserved)")
    if has_chart:
        media_bits.append("chart placeholder")
    if has_table:
        media_bits.append("table placeholder")
    if media_bits:
        parts.append("Includes " + ", ".join(media_bits) + ".")

    text_count = len(_content_placeholders(entry))
    if text_count:
        parts.append(f"{text_count} text placeholder(s).")

    return " ".join(parts)


def classify_layout_role_from_name(name: str) -> str:
    """Classify a layout role when only the layout name is available."""
    return classify_layout_role(LayoutEntry(name=name, placeholders=[]))


def layout_role_for_entry(entry: LayoutEntry) -> str:
    """Return the effective role for an entry, preferring a precomputed value."""
    if entry.role and entry.role != "content":
        return entry.role
    computed = classify_layout_role(entry)
    if computed != "content":
        return computed
    return entry.role or computed


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

    roles = {index: layout_role_for_entry(entry) for index, entry in layout.layouts.items()}
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


def is_text_placeholder(ph_type: str) -> bool:
    """Return True when a placeholder type is text-fillable."""
    upper = ph_type.upper()
    if any(keyword in upper for keyword in _GRAPHIC_PLACEHOLDER_KEYWORDS):
        if "OBJECT" in upper and not any(k in upper for k in ("PICTURE", "CHART", "TABLE", "MEDIA")):
            return True
        if "PICTURE" in upper or "CHART" in upper or "TABLE" in upper or "MEDIA" in upper:
            return False
    return any(keyword in upper for keyword in _TEXT_PLACEHOLDER_KEYWORDS) or "OBJECT" in upper
