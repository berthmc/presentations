"""Tests for pipeline state schema."""

from presentations.core.schemas import GenerateRequest
from presentations.core.state import PipelineState, ResearchPayload, ResearchSnippet


def test_research_payload_to_prompt_text() -> None:
    payload = ResearchPayload(
        snippets=[
            ResearchSnippet(
                claim="Revenue grew 12%",
                source_quote="FY24 revenue +12% YoY",
                doc_id="annual_report",
                slide_topic_hint="Financial summary",
            )
        ]
    )
    text = payload.to_prompt_text()
    assert "Revenue grew 12%" in text
    assert "annual_report" in text
    assert "Financial summary" in text


def test_pipeline_state_defaults() -> None:
    state = PipelineState(request=GenerateRequest(brief="Test brief"))
    assert state.revision == 0
    assert state.max_revisions == 3
    assert state.research.snippets == []
