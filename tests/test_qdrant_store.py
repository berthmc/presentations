"""Tests for Qdrant vector store helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from presentations.rag import qdrant_store


def test_search_uses_query_points_api() -> None:
    """search() should call query_points (not the removed search API)."""
    hit = SimpleNamespace(
        score=0.92,
        payload={"text": "chunk text", "doc_id": "doc-1", "chunk_index": 2},
    )
    client = MagicMock()
    client.query_points.return_value = SimpleNamespace(points=[hit])

    with patch.object(qdrant_store, "_get_client", return_value=client):
        results = qdrant_store.search([0.1, 0.2], top_k=3)

    client.query_points.assert_called_once()
    call_kwargs = client.query_points.call_args.kwargs
    assert call_kwargs["query"] == [0.1, 0.2]
    assert call_kwargs["limit"] == 3
    assert call_kwargs["with_payload"] is True
    assert results == [
        {
            "text": "chunk text",
            "doc_id": "doc-1",
            "score": 0.92,
            "chunk_index": 2,
        }
    ]


def test_search_applies_doc_id_filter() -> None:
    """search() should pass a doc_id filter when requested."""
    client = MagicMock()
    client.query_points.return_value = SimpleNamespace(points=[])

    with patch.object(qdrant_store, "_get_client", return_value=client):
        qdrant_store.search([0.1], top_k=1, doc_id="brief-42")

    query_filter = client.query_points.call_args.kwargs["query_filter"]
    assert query_filter is not None
    assert query_filter.must[0].key == "doc_id"
    assert query_filter.must[0].match.value == "brief-42"
