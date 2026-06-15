"""Visual and geometric QA auditing."""

from pathlib import Path

from loguru import logger
from PIL import Image

from presentations.core.schemas import QAIssue, QAReport
from presentations.llm.router import LLMRouter

VLM_AUDIT_PROMPT = """Inspect this rendered slide image for visual bugs. Identify if any text overlaps other text,
if bullet points collide with shapes, or if text contrast is illegible.
Return strict JSON: {"passed": boolean, "reasons": ["..."]}
"""


def _check_geometric(image_path: Path, slide_number: int) -> list[QAIssue]:
    """Run lightweight geometric heuristics on a slide image."""
    issues: list[QAIssue] = []
    with Image.open(image_path) as img:
        width, height = img.size
        margin_px = int(min(width, height) * 0.03)
        rgb = img.convert("RGB")
        # Sample edge pixels for potential content clipping (very dark/bright at edges)
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


async def audit_slide_images(
    image_paths: list[str | Path],
    allow_cloud: bool = False,
) -> QAReport:
    """Audit rendered slide images with geometry + optional VLM."""
    router = LLMRouter(allow_cloud=allow_cloud)
    vision = await router.get_vision_provider()
    all_issues: list[QAIssue] = []
    all_reasons: list[str] = []
    slide_image_strs = [str(Path(p).resolve()) for p in image_paths]

    for index, image_path in enumerate(image_paths, start=1):
        path = Path(image_path)
        all_issues.extend(_check_geometric(path, index))

        if vision is not None:
            try:
                result = await vision.audit_slide_image(str(path), VLM_AUDIT_PROMPT)
                if not result.get("passed", False):
                    for reason in result.get("reasons", []):
                        all_reasons.append(reason)
                        all_issues.append(
                            QAIssue(slide=index, severity="error", category="vlm", message=str(reason))
                        )
            except Exception as exc:
                logger.warning("VLM audit failed for slide {}: {}", index, exc)
                all_issues.append(
                    QAIssue(
                        slide=index,
                        severity="warning",
                        category="vlm",
                        message=f"VLM audit unavailable: {exc}",
                    )
                )

    passed = not any(issue.severity == "error" for issue in all_issues)
    return QAReport(
        passed=passed,
        reasons=all_reasons,
        issues=all_issues,
        slide_images=slide_image_strs,
    )
