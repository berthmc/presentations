"""Tests for async generation job store."""

import pytest
from presentations.core.schemas import DeckSpec, GenerateResult, GenerationMode
from presentations.core.state import PipelineStage
from presentations.services.job_store import JobStatus, get_job_store, reset_job_store


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    reset_job_store()


@pytest.mark.asyncio
async def test_job_store_create_and_update() -> None:
    store = get_job_store()
    job_id = await store.create()

    record = await store.get(job_id)
    assert record is not None
    assert record.status == JobStatus.QUEUED

    updated = await store.update(job_id, status=JobStatus.RUNNING, stage=PipelineStage.PLAN)
    assert updated is not None
    assert updated.status == JobStatus.RUNNING
    assert updated.stage == PipelineStage.PLAN

    result = GenerateResult(
        output_path="/tmp/demo.pptx",
        deck_spec=DeckSpec(title="Demo", mode=GenerationMode.SCRATCH, slides=[]),
        qa_report=None,
        layout_profile=None,
    )
    done = await store.update(job_id, status=JobStatus.DONE, result=result)
    assert done is not None
    assert done.result is not None
    assert done.result.output_path == "/tmp/demo.pptx"


@pytest.mark.asyncio
async def test_job_store_status_response_excludes_result_by_default() -> None:
    store = get_job_store()
    job_id = await store.create()
    result = GenerateResult(
        output_path="/tmp/demo.pptx",
        deck_spec=DeckSpec(title="Demo", mode=GenerationMode.SCRATCH, slides=[]),
        qa_report=None,
        layout_profile=None,
    )
    record = await store.update(job_id, status=JobStatus.DONE, result=result)
    assert record is not None

    response = store.to_status_response(record)
    assert response.status == JobStatus.DONE
    assert response.result is None

    response_with_result = store.to_status_response(record, include_result=True)
    assert response_with_result.result is not None
