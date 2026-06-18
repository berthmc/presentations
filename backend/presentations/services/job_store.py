"""In-memory job store for async presentation generation."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel

from presentations.core.schemas import GenerateResult
from presentations.core.state import PipelineStage


class JobStatus(StrEnum):
    """Lifecycle status for a generation job."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobRecord(BaseModel):
    """Persisted state for one generation job."""

    job_id: str
    status: JobStatus
    stage: PipelineStage | None = None
    result: GenerateResult | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class JobStatusResponse(BaseModel):
    """Public job status payload returned by polling endpoints."""

    job_id: str
    status: JobStatus
    stage: PipelineStage | None = None
    error: str | None = None
    result: GenerateResult | None = None


class JobStore:
    """Thread-safe in-memory store for generation jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self) -> str:
        """Create a queued job and return its identifier."""
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        record = JobRecord(
            job_id=job_id,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._jobs[job_id] = record
        return job_id

    async def get(self, job_id: str) -> JobRecord | None:
        """Return a job record if it exists."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        stage: PipelineStage | None = None,
        result: GenerateResult | None = None,
        error: str | None = None,
    ) -> JobRecord | None:
        """Update fields on an existing job record."""
        async with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            updates: dict[str, object] = {"updated_at": datetime.now(UTC).isoformat()}
            if status is not None:
                updates["status"] = status
            if stage is not None:
                updates["stage"] = stage
            if result is not None:
                updates["result"] = result
            if error is not None:
                updates["error"] = error
            updated = record.model_copy(update=updates)
            self._jobs[job_id] = updated
            return updated

    def to_status_response(self, record: JobRecord, *, include_result: bool = False) -> JobStatusResponse:
        """Convert an internal record to an API response."""
        return JobStatusResponse(
            job_id=record.job_id,
            status=record.status,
            stage=record.stage,
            error=record.error,
            result=record.result if include_result else None,
        )


_store: JobStore | None = None


def get_job_store() -> JobStore:
    """Return the process-wide job store singleton."""
    global _store
    if _store is None:
        _store = JobStore()
    return _store


def reset_job_store() -> None:
    """Reset the job store singleton (testing helper)."""
    global _store
    _store = JobStore()
