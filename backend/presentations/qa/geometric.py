"""Lightweight geometric heuristics for slide images."""

from pathlib import Path

from PIL import Image

from presentations.core.schemas import QAIssue


def check_geometric(image_path: Path, slide_number: int) -> list[QAIssue]:
    """Run lightweight geometric heuristics on a slide image."""
    issues: list[QAIssue] = []
    with Image.open(image_path) as img:
        width, height = img.size
        margin_px = int(min(width, height) * 0.03)
        rgb = img.convert("RGB")
        edge_samples = []
        for x in range(0, width, max(1, width // 20)):
            edge_samples.append(rgb.getpixel((x, margin_px)))
            edge_samples.append(rgb.getpixel((x, height - margin_px - 1)))
        avg_brightness = sum(sum(p) for p in edge_samples) / (len(edge_samples) * 3)
        if avg_brightness < 10 or avg_brightness > 245:
            issues.append(
                QAIssue(
                    slide=slide_number,
                    severity="warning",
                    category="margin",
                    message="Edge contrast suggests possible content clipping or insufficient margins",
                )
            )
    return issues
