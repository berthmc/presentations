"""Visual and geometric QA auditing."""

from pathlib import Path

from loguru import logger

from presentations.agents.skill_rules import VISUAL_QA_PROMPT
from presentations.core.schemas import QAIssue, QAReport
from presentations.llm.router import LLMRouter
from presentations.qa.geometric import check_geometric

VLM_AUDIT_PROMPT = VISUAL_QA_PROMPT


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
        all_issues.extend(check_geometric(path, index))

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
