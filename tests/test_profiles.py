"""Hardware profile tests."""

from presentations.config.settings import Settings
from presentations.core.profiles import (
    INTEGRATED_PROFILE,
    resolve_effective_supports_vlm,
    resolve_model_profile,
    run_hardware_diagnostics,
)


def test_resolve_model_profile_returns_profile() -> None:
    profile = resolve_model_profile()
    assert profile.synthesis_model
    assert profile.vlm_model


def test_hardware_diagnostics_payload() -> None:
    diag = run_hardware_diagnostics()
    assert "active_profile" in diag
    assert "synthesis_model" in diag
    assert "supports_vlm" in diag


def test_resolve_effective_supports_vlm_honours_override() -> None:
    settings = Settings(OLLAMA_SUPPORTS_VLM=True)
    assert resolve_effective_supports_vlm(INTEGRATED_PROFILE, settings) is True

    settings = Settings(OLLAMA_SUPPORTS_VLM=False)
    assert resolve_effective_supports_vlm(INTEGRATED_PROFILE, settings) is False


def test_resolve_effective_supports_vlm_defers_to_profile() -> None:
    settings = Settings(_env_file=None, ollama_supports_vlm=None)
    assert resolve_effective_supports_vlm(INTEGRATED_PROFILE, settings) is False
