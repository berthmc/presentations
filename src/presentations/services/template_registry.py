"""Persistent template library backed by JSON registry and on-disk files."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from loguru import logger

from presentations.config.settings import Settings, get_settings
from presentations.core.templates import ResolvedTemplate, TemplateRecord, TemplateSummary
from presentations.ingest.discover import discover_layout

ALLOWED_SUFFIXES = {".pptx", ".md"}


class TemplateRegistry:
    """CRUD operations for the template library."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.registry_path = self.settings.templates_dir / "registry.json"
        self.settings.templates_dir.mkdir(parents=True, exist_ok=True)

    def _load_records(self) -> list[TemplateRecord]:
        if not self.registry_path.exists():
            return []
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return [TemplateRecord.model_validate(item) for item in raw.get("templates", [])]

    def _save_records(self, records: list[TemplateRecord]) -> None:
        payload = {"templates": [record.model_dump(mode="json") for record in records]}
        self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def list_templates(self) -> list[TemplateSummary]:
        """Return all templates as summaries, default first."""
        records = self._load_records()
        records.sort(key=lambda record: (not record.is_default, record.name.lower()))
        return [record.summary() for record in records]

    def get_template(self, template_id: str) -> TemplateRecord:
        """Return a template by id."""
        for record in self._load_records():
            if record.id == template_id:
                return record
        raise KeyError(f"Template not found: {template_id}")

    def get_default(self) -> TemplateRecord | None:
        """Return the default template if one is set."""
        for record in self._load_records():
            if record.is_default:
                return record
        records = self._load_records()
        return records[0] if records else None

    def register(
        self,
        name: str,
        source_path: Path,
        *,
        is_default: bool = False,
        original_filename: str | None = None,
    ) -> TemplateRecord:
        """Register a template file in the library.

        Args:
            name: User-facing template name.
            source_path: Path to an existing .pptx or .md file.
            is_default: Whether to mark this template as the default selection.
            original_filename: Original upload filename for display.

        Returns:
            The created TemplateRecord.
        """
        source = Path(source_path).resolve()
        suffix = source.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ValueError(f"Unsupported template type: {suffix}. Use .pptx or .md")

        template_id = uuid4().hex
        dest_dir = self.settings.templates_dir / template_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"template{suffix}"
        shutil.copy2(source, dest_file)

        layout_profile = discover_layout(dest_file)
        layout_profile.source_path = str(dest_file)

        now = datetime.now(timezone.utc)
        record = TemplateRecord(
            id=template_id,
            name=name.strip(),
            file_path=str(dest_file),
            source_type=layout_profile.source_type,
            layout_profile=layout_profile,
            is_default=is_default,
            original_filename=original_filename or source.name,
            created_at=now,
            updated_at=now,
        )

        records = self._load_records()
        if is_default or not records:
            for existing in records:
                existing.is_default = False
            record.is_default = True

        records.append(record)
        self._save_records(records)
        logger.info("Registered template '{}' ({})", record.name, record.id)
        return record

    def delete(self, template_id: str) -> None:
        """Delete a template from the library."""
        records = self._load_records()
        remaining: list[TemplateRecord] = []
        deleted: TemplateRecord | None = None
        for record in records:
            if record.id == template_id:
                deleted = record
                continue
            remaining.append(record)

        if deleted is None:
            raise KeyError(f"Template not found: {template_id}")

        template_dir = self.settings.templates_dir / template_id
        if template_dir.exists():
            shutil.rmtree(template_dir)

        if deleted.is_default and remaining:
            remaining[0].is_default = True

        self._save_records(remaining)
        logger.info("Deleted template {}", template_id)

    def set_default(self, template_id: str) -> TemplateRecord:
        """Mark a template as the default selection."""
        records = self._load_records()
        target: TemplateRecord | None = None
        for record in records:
            record.is_default = record.id == template_id
            if record.id == template_id:
                target = record
                record.updated_at = datetime.now(timezone.utc)
        if target is None:
            raise KeyError(f"Template not found: {template_id}")
        self._save_records(records)
        return target

    def resolve(
        self,
        *,
        template_id: str | None = None,
        template_path: str | None = None,
    ) -> ResolvedTemplate | None:
        """Resolve a template from id or path.

        Args:
            template_id: Library template id (preferred).
            template_path: Ad-hoc filesystem path (legacy).

        Returns:
            ResolvedTemplate or None when no template specified.
        """
        if template_id:
            record = self.get_template(template_id)
            path = Path(record.file_path)
            if not path.exists():
                raise FileNotFoundError(f"Template file missing: {path}")
            return ResolvedTemplate(
                template_id=record.id,
                template_path=str(path.resolve()),
                layout_profile=record.layout_profile,
                source_type=record.source_type,
            )

        if template_path:
            path = Path(template_path).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")
            profile = discover_layout(path)
            return ResolvedTemplate(
                template_id=None,
                template_path=str(path),
                layout_profile=profile,
                source_type=profile.source_type,
            )

        return None

    def seed_builtin_templates(self) -> None:
        """Register bundled sample templates when the library is empty."""
        if self._load_records():
            return
        repo_root = Path(__file__).resolve().parents[3]
        sample = repo_root / "templates" / "sample-deck.md"
        if sample.exists():
            self.register("MD3 Sample Deck", sample, is_default=True, original_filename=sample.name)
            logger.info("Seeded built-in template library with {}", sample.name)


_registry: TemplateRegistry | None = None


def get_template_registry() -> TemplateRegistry:
    """Return cached template registry singleton."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
        _registry.seed_builtin_templates()
    return _registry
