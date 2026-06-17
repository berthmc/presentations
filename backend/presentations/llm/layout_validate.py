"""Validate and sanitize deck specs against discovered layout profiles."""

from loguru import logger

from presentations.core.schemas import DeckSpec, LayoutProfile, PlaceholderMapping, SlideSpec


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

    return deck.model_copy(update={"slides": sanitized_slides})
