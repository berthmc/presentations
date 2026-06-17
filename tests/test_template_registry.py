"""Template registry tests."""

from pathlib import Path

import pytest

import presentations.config.settings as settings_module
from presentations.config.settings import Settings
from presentations.services.template_registry import TemplateRegistry


@pytest.fixture
def registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TemplateRegistry:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_module._settings = None
    settings = Settings()
    settings.ensure_dirs()
    return TemplateRegistry(settings=settings)


def test_register_and_list_md_template(registry: TemplateRegistry) -> None:
    sample = Path("templates/sample-deck.md")
    record = registry.register("Test Deck", sample, is_default=True)
    assert record.id
    assert record.is_default
    summaries = registry.list_templates()
    assert len(summaries) == 1
    assert summaries[0].name == "Test Deck"


def test_resolve_by_template_id(registry: TemplateRegistry) -> None:
    sample = Path("templates/sample-deck.md")
    record = registry.register("Resolve Test", sample)
    resolved = registry.resolve(template_id=record.id)
    assert resolved is not None
    assert resolved.template_path.endswith("template.md")
    assert resolved.layout_profile.layouts


def test_set_default_and_delete(registry: TemplateRegistry) -> None:
    sample = Path("templates/sample-deck.md")
    first = registry.register("First", sample, is_default=True)
    second = registry.register("Second", sample)
    registry.set_default(second.id)
    updated = registry.get_template(second.id)
    assert updated.is_default
    registry.delete(first.id)
    assert len(registry.list_templates()) == 1


def test_resolve_missing_template_raises(registry: TemplateRegistry) -> None:
    with pytest.raises(KeyError):
        registry.resolve(template_id="missing-id")


def test_get_default_pptx_prefers_first_pptx_when_default_is_md(registry: TemplateRegistry) -> None:
    """get_default_pptx should return the first .pptx template when the default is .md."""
    sample = Path("templates/sample-deck.md")
    registry.register("MD Layout", sample, is_default=True)
    pptx_record = registry.register("Corporate Deck", sample)

    records = registry._load_records()
    for record in records:
        if record.id == pptx_record.id:
            record.source_type = "pptx"
    registry._save_records(records)

    default_pptx = registry.get_default_pptx()
    assert default_pptx is not None
    assert default_pptx.id == pptx_record.id


def test_get_default_pptx_returns_none_when_only_md_templates(registry: TemplateRegistry) -> None:
    sample = Path("templates/sample-deck.md")
    registry.register("MD Layout", sample, is_default=True)
    assert registry.get_default_pptx() is None
