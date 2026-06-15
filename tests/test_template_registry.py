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
