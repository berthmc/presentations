"""Tests for generation context resolution."""

from unittest.mock import MagicMock

import pytest

from presentations.core.schemas import GenerateRequest, GenerationMode, LayoutProfile
from presentations.core.templates import ResolvedTemplate
from presentations.services.generation_context import (
    resolve_allow_cloud,
    resolve_generation_context,
)


def test_template_mode_without_id_uses_default_pptx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Template mode should fall back to the default .pptx template when no id is supplied."""
    registry = MagicMock()
    default_record = MagicMock()
    default_record.id = "pptx-default"
    registry.get_default_pptx.return_value = default_record
    layout_profile = LayoutProfile(
        source_path="/data/templates/pptx-default/template.pptx",
        source_type="pptx",
        layouts={},
    )
    registry.resolve.return_value = ResolvedTemplate(
        template_id="pptx-default",
        template_path="/data/templates/pptx-default/template.pptx",
        layout_profile=layout_profile,
        source_type="pptx",
    )
    monkeypatch.setattr("presentations.services.generation_context.get_template_registry", lambda: registry)

    request = GenerateRequest(brief="Quarterly update", mode=GenerationMode.TEMPLATE, run_qa=False)
    template_path, _layout_profile, mode = resolve_generation_context(request)

    assert mode == GenerationMode.TEMPLATE
    assert template_path == "/data/templates/pptx-default/template.pptx"
    registry.get_default_pptx.assert_called_once()
    registry.resolve.assert_called_once_with(template_id="pptx-default", template_path=None)


def test_template_mode_with_template_id_skips_default_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit template_id should be used without consulting the default .pptx template."""
    registry = MagicMock()
    layout_profile = LayoutProfile(
        source_path="/data/templates/explicit-id/template.pptx",
        source_type="pptx",
        layouts={},
    )
    registry.resolve.return_value = ResolvedTemplate(
        template_id="explicit-id",
        template_path="/data/templates/explicit-id/template.pptx",
        layout_profile=layout_profile,
        source_type="pptx",
    )
    monkeypatch.setattr("presentations.services.generation_context.get_template_registry", lambda: registry)

    request = GenerateRequest(
        brief="Quarterly update",
        template_id="explicit-id",
        mode=GenerationMode.TEMPLATE,
        run_qa=False,
    )
    resolve_generation_context(request)

    registry.get_default_pptx.assert_not_called()
    registry.resolve.assert_called_once_with(template_id="explicit-id", template_path=None)


def test_template_mode_without_pptx_template_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Template mode should fail clearly when no .pptx template exists."""
    registry = MagicMock()
    registry.get_default_pptx.return_value = None
    registry.resolve.return_value = None
    monkeypatch.setattr("presentations.services.generation_context.get_template_registry", lambda: registry)

    request = GenerateRequest(brief="Quarterly update", mode=GenerationMode.TEMPLATE, run_qa=False)
    with pytest.raises(ValueError, match="template_id or template_path required"):
        resolve_generation_context(request)


def test_resolve_allow_cloud_requires_explicit_user_opt_in() -> None:
    """Cloud LLM is only used when the request explicitly opts in."""
    request = GenerateRequest(brief="Update", run_qa=False, allow_cloud=False)
    assert resolve_allow_cloud(request) is False

    request_opted_in = GenerateRequest(brief="Update", run_qa=False, allow_cloud=True)
    assert resolve_allow_cloud(request_opted_in) is True
