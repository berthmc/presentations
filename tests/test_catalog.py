"""Model catalog tests."""

from presentations.llm.catalog import GEMINI_MODEL_IDS, MODEL_CATALOG, is_gemini_model_id


def test_model_catalog_has_entries() -> None:
    assert len(MODEL_CATALOG) >= 2
    providers = {entry.provider for entry in MODEL_CATALOG}
    assert "ollama" in providers
    assert "gemini" in providers


def test_is_gemini_model_id() -> None:
    assert is_gemini_model_id("gemini-2.0-flash")
    assert is_gemini_model_id(next(iter(GEMINI_MODEL_IDS)))
    assert not is_gemini_model_id("qwen2.5:3b")
