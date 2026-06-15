import { useCallback, useEffect, useState } from "react";
import {
  deleteTemplate,
  listTemplates,
  registerTemplate,
  setDefaultTemplate,
} from "../api/client";
import type { TemplateSummary } from "../types";

interface Props {
  selectedId: string;
  onSelect: (id: string) => void;
  onModeHint: (mode: "scratch" | "template") => void;
}

export function TemplateLibrary({ selectedId, onSelect, onModeHint }: Props) {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [name, setName] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const payload = await listTemplates();
    setTemplates(payload.templates);
    const defaultTemplate =
      payload.templates.find((item) => item.is_default) ?? payload.templates[0];
    if (defaultTemplate && !selectedId) {
      onSelect(defaultTemplate.id);
      if (defaultTemplate.source_type === "pptx") {
        onModeHint("template");
      }
    }
  }, [onModeHint, onSelect, selectedId]);

  useEffect(() => {
    refresh().catch((err: Error) => setStatus(err.message));
  }, [refresh]);

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!name.trim()) {
      setStatus("Enter a template name before uploading.");
      return;
    }
    setBusy(true);
    try {
      await registerTemplate(name.trim(), file, isDefault);
      setStatus(`Registered template "${name.trim()}"`);
      setName("");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function handleSetDefault() {
    if (!selectedId) return;
    setBusy(true);
    try {
      await setDefaultTemplate(selectedId);
      setStatus("Default template updated.");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!selectedId) return;
    setBusy(true);
    try {
      await deleteTemplate(selectedId);
      setStatus("Template deleted.");
      onSelect("");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  function handleSelectChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const id = event.target.value;
    onSelect(id);
    const selected = templates.find((item) => item.id === id);
    if (selected?.source_type === "pptx") {
      onModeHint("template");
    }
  }

  return (
    <section className="md3-card">
      <h2>Template Library</h2>
      <div className="field">
        <label htmlFor="template-select">Saved template</label>
        <select id="template-select" value={selectedId} onChange={handleSelectChange}>
          <option value="">None</option>
          {templates.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name} ({template.source_type})
              {template.is_default ? " *" : ""}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="template-name">Template name</label>
        <input
          id="template-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="e.g. Acme Corporate 2026"
        />
      </div>
      <div className="checkbox-row">
        <input
          id="template-default"
          type="checkbox"
          checked={isDefault}
          onChange={(event) => setIsDefault(event.target.checked)}
        />
        <label htmlFor="template-default">Set as default</label>
      </div>
      <div className="field">
        <label htmlFor="template-file">Upload .pptx or .md template</label>
        <input id="template-file" type="file" accept=".pptx,.md" onChange={handleUpload} disabled={busy} />
      </div>
      <div className="btn-row">
        <button type="button" className="outline" onClick={handleSetDefault} disabled={!selectedId || busy}>
          Set default
        </button>
        <button type="button" className="danger" onClick={handleDelete} disabled={!selectedId || busy}>
          Delete
        </button>
      </div>
      <p className="status">{status || `${templates.length} template(s) in library`}</p>
    </section>
  );
}
