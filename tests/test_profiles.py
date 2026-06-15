"""Hardware profile tests."""

from presentations.core.profiles import resolve_model_profile, run_hardware_diagnostics


def test_resolve_model_profile_returns_profile() -> None:
    profile = resolve_model_profile()
    assert profile.synthesis_model
    assert profile.vlm_model


def test_hardware_diagnostics_payload() -> None:
    diag = run_hardware_diagnostics()
    assert "active_profile" in diag
    assert "synthesis_model" in diag
