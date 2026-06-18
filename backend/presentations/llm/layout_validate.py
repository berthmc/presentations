"""Validate and sanitize deck specs against discovered layout profiles."""

from loguru import logger

from presentations.core.layout_roles import (
    body_placeholders,
    enforce_structural_layouts,
    layout_role_for_entry,
    remap_content_off_dividers,
    title_placeholder,
)
from presentations.core.schemas import DeckSpec, LayoutEntry, LayoutProfile, PlaceholderMapping, SlideSpec

_GENERIC_TITLE_LABELS = frozenset(
    {
        "title slide",
        "title",
        "click to add title",
        "click to edit master title style",
        "subtitle",
        "content placeholder",
        "cover page",
    }
)


def layout_validation_errors(deck: DeckSpec, layout: LayoutProfile) -> list[str]:
    """Return human-readable errors when deck indices fall outside the layout profile."""
    errors: list[str] = []
    if not layout.layouts:
        return errors

    valid_layouts = sorted(layout.layouts.keys())
    for slide_num, slide in enumerate(deck.slides, start=1):
        if slide.layout_index not in layout.layouts:
            errors.append(
                f"Slide {slide_num}: layout_index {slide.layout_index} is invalid. "
                f"Use one of {valid_layouts}."
            )
            continue

        allowed_ph = sorted(ph.index for ph in layout.layouts[slide.layout_index].placeholders)
        if not allowed_ph:
            errors.append(f"Slide {slide_num}: layout {slide.layout_index} has no placeholders.")
            continue

        used_ph = [mapping.ph_idx for mapping in slide.mappings]
        invalid_ph = sorted({ph_idx for ph_idx in used_ph if ph_idx not in allowed_ph})
        if invalid_ph:
            errors.append(
                f"Slide {slide_num}: ph_idx {invalid_ph} invalid for layout {slide.layout_index}. "
                f"Allowed ph_idx for this layout: {allowed_ph}."
            )
    return errors


def validate_deck_against_layout(deck: DeckSpec, layout: LayoutProfile) -> None:
    """Raise ValueError when the deck references unknown layouts or placeholder indices."""
    errors = layout_validation_errors(deck, layout)
    if errors:
        raise ValueError("; ".join(errors))


def _generic_title_labels(layout: LayoutProfile) -> set[str]:
    """Return generic placeholder labels and all layout names for title-artifact detection."""
    labels = set(_GENERIC_TITLE_LABELS)
    for entry in layout.layouts.values():
        labels.add(entry.name.strip().casefold())
    return labels


def _is_generic_title_content(content: str, entry: LayoutEntry, generic_labels: set[str]) -> bool:
    """Return True when title placeholder content is a meta-label rather than real title text."""
    normalized = content.strip().casefold()
    if not normalized:
        return True
    if normalized in generic_labels:
        return True
    return normalized == entry.name.strip().casefold()


def _fix_title_slide_artifact(deck: DeckSpec, layout: LayoutProfile) -> DeckSpec:
    """Replace generic slide-1 title text (e.g. 'Title Slide') with the deck title."""
    if not deck.slides or not layout.layouts:
        return deck

    first_slide = deck.slides[0]
    entry = layout.layouts.get(first_slide.layout_index)
    if entry is None:
        return deck

    title_ph = title_placeholder(entry)
    if title_ph is None:
        return deck

    generic_labels = _generic_title_labels(layout)
    updated_mappings: list[PlaceholderMapping] = []
    changed = False
    for mapping in first_slide.mappings:
        if mapping.ph_idx != title_ph.index:
            updated_mappings.append(mapping)
            continue
        if _is_generic_title_content(mapping.content, entry, generic_labels):
            updated_mappings.append(PlaceholderMapping(ph_idx=mapping.ph_idx, content=deck.title))
            changed = True
            logger.info("Replaced generic slide-1 title {!r} with deck title", mapping.content.strip())
        else:
            updated_mappings.append(mapping)

    if not changed:
        return deck

    slides = list(deck.slides)
    slides[0] = SlideSpec(
        layout_index=first_slide.layout_index,
        mappings=updated_mappings,
        notes=first_slide.notes,
    )
    return deck.model_copy(update={"slides": slides})


def _distribute_multicolumn_content(slide: SlideSpec, entry: LayoutEntry) -> SlideSpec:
    """Spread multi-line body content across all body columns when only one column was filled."""
    bodies = body_placeholders(entry)
    if len(bodies) < 2:
        return slide

    body_indices = {ph.index for ph in bodies}
    mappings_by_ph = {mapping.ph_idx: mapping for mapping in slide.mappings}
    filled_bodies = [
        ph
        for ph in bodies
        if ph.index in mappings_by_ph and mappings_by_ph[ph.index].content.strip()
    ]
    if len(filled_bodies) != 1:
        return slide

    source_content = mappings_by_ph[filled_bodies[0].index].content
    lines = [line.strip() for line in source_content.split("\n") if line.strip()]
    if len(lines) <= 1:
        return slide

    distributed: dict[int, list[str]] = {ph.index: [] for ph in bodies}
    for index, line in enumerate(lines):
        target = bodies[index % len(bodies)]
        distributed[target.index].append(line)

    non_body_mappings = [mapping for mapping in slide.mappings if mapping.ph_idx not in body_indices]
    new_mappings = list(non_body_mappings)
    for ph in bodies:
        column_content = "\n".join(distributed[ph.index])
        if column_content:
            new_mappings.append(PlaceholderMapping(ph_idx=ph.index, content=column_content))

    logger.info(
        "Distributed {} lines across {} body columns on layout {}",
        len(lines),
        len(bodies),
        entry.name,
    )
    return SlideSpec(layout_index=slide.layout_index, mappings=new_mappings, notes=slide.notes)


def _apply_multicolumn_distribution(deck: DeckSpec, layout: LayoutProfile) -> DeckSpec:
    """Apply multi-column distribution to every slide in the deck."""
    slides: list[SlideSpec] = []
    for slide in deck.slides:
        entry = layout.layouts.get(slide.layout_index)
        if entry is None:
            slides.append(slide)
            continue
        if layout_role_for_entry(entry) == "two-content" or len(body_placeholders(entry)) >= 2:
            slides.append(_distribute_multicolumn_content(slide, entry))
        else:
            slides.append(slide)
    return deck.model_copy(update={"slides": slides})


def sanitize_deck_spec(deck: DeckSpec, layout: LayoutProfile) -> DeckSpec:
    """Clamp deck slides to valid layout and placeholder indices before compile."""
    if not layout.layouts:
        return deck

    default_layout = min(layout.layouts.keys())
    sanitized_slides: list[SlideSpec] = []

    for slide_num, slide in enumerate(deck.slides, start=1):
        layout_index = slide.layout_index
        if layout_index not in layout.layouts:
            logger.warning(
                "Slide {}: replacing invalid layout_index {} with {}",
                slide_num,
                layout_index,
                default_layout,
            )
            layout_index = default_layout

        entry = layout.layouts[layout_index]
        allowed_ph = {ph.index for ph in entry.placeholders}
        if not allowed_ph:
            sanitized_slides.append(SlideSpec(layout_index=layout_index, mappings=[], notes=slide.notes))
            continue

        kept: list[PlaceholderMapping] = []
        orphan_content: list[str] = []
        for mapping in slide.mappings:
            if mapping.ph_idx in allowed_ph:
                kept.append(mapping)
            else:
                orphan_content.append(mapping.content)
                logger.warning(
                    "Slide {}: dropping invalid ph_idx {} on layout {} (allowed: {})",
                    slide_num,
                    mapping.ph_idx,
                    layout_index,
                    sorted(allowed_ph),
                )

        if not kept and orphan_content:
            fallback_ph = min(allowed_ph)
            merged = "\n".join(part for part in orphan_content if part.strip())
            kept = [PlaceholderMapping(ph_idx=fallback_ph, content=merged)]
            logger.warning(
                "Slide {}: remapped orphan content to ph_idx {} on layout {}",
                slide_num,
                fallback_ph,
                layout_index,
            )

        sanitized_slides.append(
            SlideSpec(layout_index=layout_index, mappings=kept, notes=slide.notes)
        )

    sanitized = deck.model_copy(update={"slides": sanitized_slides})
    sanitized = _fix_title_slide_artifact(sanitized, layout)
    sanitized = _apply_multicolumn_distribution(sanitized, layout)
    sanitized = enforce_structural_layouts(sanitized, layout)
    sanitized = remap_content_off_dividers(sanitized, layout)
    return sanitized
