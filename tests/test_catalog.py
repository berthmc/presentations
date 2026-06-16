"""Model catalog tests."""

from presentations.llm.catalog import GEMINI_MODEL_IDS, MODEL_CATALOG, is_gemini_model_id, is_vllm_model_id


def test_model_catalog_has_entries() -> None:
    assert len(MODEL_CATALOG) >= 2
    providers = {entry.provider for entry in MODEL_CATALOG}
    assert "ollama" in providers
    assert "gemini" in providers
    assert "vllm" in providers


def test_is_gemini_model_id() -> None:
    assert is_gemini_model_id("gemini-2.0-flash")
    assert is_gemini_model_id(next(iter(GEMINI_MODEL_IDS)))
    assert not is_gemini_model_id("qwen2.5:3b")
    assert not is_gemini_model_id("llama3.2:3b")


def test_is_vllm_model_id() -> None:
    assert is_vllm_model_id("qwen2.5-coder:14b-awq")
    assert not is_vllm_model_id("qwen2.5:7b")


def test_model_catalog_includes_installed_local_models() -> None:
    local_ids = {entry.id for entry in MODEL_CATALOG if entry.provider == "ollama"}
    assert {"qwen2.5:7b", "qwen2.5:3b", "llama3.2:3b"}.issubset(local_ids)
