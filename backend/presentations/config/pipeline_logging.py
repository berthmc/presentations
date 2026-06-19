"""Structured logging helpers for the five-stage presentation pipeline."""

from __future__ import annotations

import time
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from loguru import logger

from presentations.core.schemas import DeckSpec
from presentations.core.state import PipelineStage

STAGE_ORDER: list[tuple[PipelineStage, str]] = [
    (PipelineStage.RESEARCH, "research"),
    (PipelineStage.PROFILE, "profile"),
    (PipelineStage.PLAN, "plan"),
    (PipelineStage.ASSEMBLE, "assemble"),
    (PipelineStage.INSPECT, "inspect"),
]

_STAGE_INDEX: dict[PipelineStage, int] = {stage: index + 1 for index, (stage, _label) in enumerate(STAGE_ORDER)}
_STAGE_LABEL: dict[PipelineStage, str] = {stage: label for stage, label in STAGE_ORDER}


def resolve_run_id(job_id: str | None) -> str:
    """Return job_id when present, otherwise a short run identifier for log correlation."""
    if job_id:
        return job_id[:8] if len(job_id) > 8 else job_id
    return uuid4().hex[:8]


def stage_label(stage: PipelineStage) -> str:
    """Return the human-readable stage name."""
    return _STAGE_LABEL.get(stage, stage.value)


def stage_marker(stage: PipelineStage) -> str:
    """Return a marker like '1/5 research'."""
    index = _STAGE_INDEX.get(stage, 0)
    return f"{index}/5 {stage_label(stage)}"


def summarize_deck_spec(deck_spec: DeckSpec) -> dict[str, Any]:
    """Summarise a deck spec for logging."""
    layout_indices = [slide.layout_index for slide in deck_spec.slides]
    mapping_count = sum(len(slide.mappings) for slide in deck_spec.slides)
    content_chars = sum(len(mapping.content) for slide in deck_spec.slides for mapping in slide.mappings)
    layout_distribution = dict(Counter(layout_indices))
    return {
        "title": deck_spec.title,
        "slides": len(deck_spec.slides),
        "mappings": mapping_count,
        "content_chars": content_chars,
        "layouts": layout_distribution,
    }


def summarize_pptx_file(path: str | Path) -> dict[str, Any]:
    """Summarise a compiled .pptx file for logging."""
    file_path = Path(path)
    if not file_path.exists():
        return {"path": str(file_path), "exists": False, "size_kb": 0}
    size_bytes = file_path.stat().st_size
    return {
        "path": str(file_path.resolve()),
        "exists": True,
        "size_kb": round(size_bytes / 1024, 1),
    }


def format_metrics(metrics: dict[str, Any]) -> str:
    """Format metric key-value pairs for log messages."""
    return " ".join(f"{key}={value}" for key, value in metrics.items())


@asynccontextmanager
async def pipeline_stage(run_id: str, stage: PipelineStage, revision: int = 0):
    """Bind pipeline context and log stage start/complete with duration."""
    marker = stage_marker(stage)
    revision_str = str(revision)
    with logger.contextualize(run_id=run_id, stage=stage.value, revision=revision_str):
        logger.info("Pipeline stage {} started", marker)
        started = time.perf_counter()
        metrics: dict[str, Any] = {}
        failed = False
        try:
            yield metrics
        except Exception:
            failed = True
            raise
        finally:
            duration = time.perf_counter() - started
            metrics["duration_s"] = round(duration, 2)
            if failed:
                logger.error("Pipeline stage {} failed {}", marker, format_metrics(metrics))
            else:
                logger.info("Pipeline stage {} complete {}", marker, format_metrics(metrics))


def log_llm_call(
    *,
    provider: str,
    model: str,
    duration_s: float,
    prompt_chars: int,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> None:
    """Log a successful LLM JSON generation call."""
    parts = [
        f"provider={provider}",
        f"model={model}",
        f"duration_s={round(duration_s, 2)}",
        f"prompt_chars={prompt_chars}",
    ]
    if prompt_tokens is not None:
        parts.append(f"prompt_tokens={prompt_tokens}")
    if completion_tokens is not None:
        parts.append(f"completion_tokens={completion_tokens}")
    logger.info("LLM generate_json {}", " ".join(parts))
