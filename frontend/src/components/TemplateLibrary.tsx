import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";
import {
  deleteTemplate,
  listTemplates,
  registerTemplate,
  setDefaultTemplate,
} from "../api/client";
import type { TemplateSummary } from "../types";
import { TextField } from "./TextField";

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

  function handleChipSelect(template: TemplateSummary) {
    onSelect(template.id);
    if (template.source_type === "pptx") {
      onModeHint("template");
    }
  }

  return (
    <section className="md3-card">
      <header className="section-header">
        <h2>Template Library</h2>
        <span className="section-header__meta">{templates.length} template(s)</span>
      </header>

      <p className="text-field__hint" style={{ margin: "0 0 1rem" }}>
        Select a saved template or upload a new .pptx / .md layout.
      </p>

      <div className="chip-row" role="listbox" aria-label="Saved templates">
        {templates.length === 0 && (
          <span className="chip chip--assist">No templates yet</span>
        )}
        {templates.map((template) => (
          <button
            key={template.id}
            type="button"
            role="option"
            aria-selected={selectedId === template.id}
            className={`chip${selectedId === template.id ? " chip--selected" : ""}`}
            onClick={() => handleChipSelect(template)}
          >
            {template.name}
            <span className="signal-tile__badge signal-tile__badge--neutral">
              {template.source_type}
            </span>
            {template.is_default && " · default"}
          </button>
        ))}
      </div>

      <TextField
        id="template-name"
        label="Template name"
        value={name}
        onChange={(event: ChangeEvent<HTMLInputElement>) => setName(event.target.value)}
      />

      <div className="checkbox-row">
        <input
          id="template-default"
          type="checkbox"
          checked={isDefault}
          onChange={(event) => setIsDefault(event.target.checked)}
        />
        <label htmlFor="template-default">Set as default</label>
      </div>

      <div className="source-doc-row">
        <input
          ref={fileInputRef}
          type="file"
          className="hidden-input"
          accept=".pptx,.md,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/markdown"
          onChange={handleFileSelect}
        />
        <button
          type="button"
          className="tonal btn-with-icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={busy}
        >
          <span className="material-symbols-rounded">upload_file</span>
          Choose file
        </button>
        {pendingFile && (
          <span className="chip chip--input">
            {pendingFile.name}
            <button
              type="button"
              className="chip__dismiss"
              aria-label="Clear selected file"
              onClick={() => setPendingFile(null)}
            >
              <span className="material-symbols-rounded">close</span>
            </button>
          </span>
        )}
        <button
          type="button"
          className="primary btn-with-icon"
          onClick={handleSave}
          disabled={busy || !pendingFile || !name.trim()}
        >
          <span className="material-symbols-rounded">save</span>
          {busy ? "Saving…" : "Save to library"}
        </button>
      </div>
      <p className="text-field__hint">Accepts .pptx and .md templates</p>

      <div className="btn-row" style={{ marginTop: "1rem" }}>
        <button
          type="button"
          className="outlined btn-with-icon"
          onClick={handleSetDefault}
          disabled={!selectedId || busy}
        >
          <span className="material-symbols-rounded">star</span>
          Set default
        </button>
        <button
          type="button"
          className="danger btn-with-icon"
          onClick={handleDelete}
          disabled={!selectedId || busy}
        >
          <span className="material-symbols-rounded">delete</span>
          Delete
        </button>
      </div>

      <p className={`status${statusIsError ? " error" : ""}`}>{status}</p>
    </section>
  );
}
