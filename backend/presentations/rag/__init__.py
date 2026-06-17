"""Local RAG stack: embeddings, Qdrant storage, indexing, retrieval."""

from presentations.rag.retriever import retrieve_research_snippets

__all__ = ["retrieve_research_snippets"]
