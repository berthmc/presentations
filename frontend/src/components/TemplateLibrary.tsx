import { useCallback, useEffect, useRef, useState } from "react";
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
  const [statusIsError, setStatusIsError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    refresh().catch((err: Error) => {
      setStatus(err.message);
      setStatusIsError(true);
    });
  }, [refresh]);

  function setInfoStatus(message: string) {
    setStatus(message);
    setStatusIsError(false);
  }

  function setErrorStatus(message: string) {
    setStatus(message);
    setStatusIsError(true);
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    setPendingFile(file);
    setInfoStatus(`Selected ${file.name}. Enter a name and click Save to library.`);
  }

  async function handleSave() {
    if (!pendingFile) {
      setErrorStatus("Choose a .pptx or .md template file first.");
      return;
    }
    if (!name.trim()) {
      setErrorStatus("Enter a template name before saving.");
      return;
    }
    setBusy(true);
    try {
      await registerTemplate(name.trim(), pendingFile, isDefault);
      setInfoStatus(`Saved template "${name.trim()}" to library`);
      setName("");
      setPendingFile(null);
      setIsDefault(false);
      await refresh();
    } catch (err) {
      setErrorStatus(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSetDefault() {
    if (!selectedId) return;
    setBusy(true);
    try {
      await setDefaultTemplate(selectedId);
      setInfoStatus("Default template updated.");
      await refresh();
    } catch (err) {
      setErrorStatus(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!selectedId) return;
    setBusy(true);
    try {
      await deleteTemplate(selectedId);
      setInfoStatus("Template deleted.");
      onSelect("");
      await refresh();
    } catch (err) {
      setErrorStatus(err instanceof Error ? err.message : "Delete failed");
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
        <label>Template file</label>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pptx,.md,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/markdown"
          hidden
          onChange={handleFileSelect}
        />
        <div className="btn-row">
          <button
            type="button"
            className="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={busy}
          >
            Choose file
          </button>
          <button
            type="button"
            className="primary"
            onClick={handleSave}
            disabled={busy || !pendingFile || !name.trim()}
          >
            {busy ? "Saving…" : "Save to library"}
          </button>
        </div>
        <p className="field-help subtle">
          {pendingFile ? `Selected: ${pendingFile.name}` : "Accepts .pptx and .md templates"}
        </p>
      </div>
      <div className="btn-row">
        <button type="button" className="outline" onClick={handleSetDefault} disabled={!selectedId || busy}>
          Set default
        </button>
        <button type="button" className="danger" onClick={handleDelete} disabled={!selectedId || busy}>
          Delete
        </button>
      </div>
      <p className={`status${statusIsError ? " error" : ""}`}>
        {status || `${templates.length} template(s) in library`}
      </p>
    </section>
  );
}
