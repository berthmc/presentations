import { useState } from "react";
import { downloadUrl, generateDeck, qaSlideUrl } from "../api/client";
import type { GenerateResult } from "../types";

interface Props {
  templateId: string;
  mode: "scratch" | "template";
  onModeChange: (mode: "scratch" | "template") => void;
  onResult: (result: GenerateResult | null) => void;
}

export function GenerateForm({ templateId, mode, onModeChange, onResult }: Props) {
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [runQa, setRunQa] = useState(false);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleGenerate() {
    if (!brief.trim()) {
      setStatus("Enter a content brief.");
      return;
    }
    setBusy(true);
    setStatus("Generating…");
    setResult(null);
    onResult(null);
    try {
      const payload = await generateDeck({
        brief,
        mode,
        title: title || undefined,
        run_qa: runQa,
        template_id: templateId || null,
      });
      setResult(payload);
      onResult(payload);
      setStatus(`Generated: ${payload.output_path}`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="md3-card">
      <h2>Generate Presentation</h2>
      <div className="field">
        <label htmlFor="title">Title</label>
        <input id="title" value={title} onChange={(event) => setTitle(event.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="mode">Mode</label>
        <select id="mode" value={mode} onChange={(event) => onModeChange(event.target.value as "scratch" | "template")}>
          <option value="scratch">scratch</option>
          <option value="template">template</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="brief">Content brief</label>
        <textarea
          id="brief"
          value={brief}
          onChange={(event) => setBrief(event.target.value)}
          placeholder="Describe the presentation you want…"
        />
      </div>
      <div className="checkbox-row">
        <input id="run-qa" type="checkbox" checked={runQa} onChange={(event) => setRunQa(event.target.checked)} />
        <label htmlFor="run-qa">Run visual QA</label>
      </div>
      <button type="button" className="primary" onClick={handleGenerate} disabled={busy}>
        {busy ? "Generating…" : "Generate"}
      </button>
      <p className={`status${status.startsWith("Error") || status.includes("failed") ? " error" : ""}`}>{status}</p>
      {result && (
        <>
          <a className="download-link" href={downloadUrl(result.output_path)}>
            Download {result.output_path.split(/[/\\]/).pop()}
          </a>
          {result.qa_report && (
            <>
              <p className="status">QA passed: {String(result.qa_report.passed)}</p>
              {result.qa_report.issues.length > 0 && (
                <ul className="qa-list">
                  {result.qa_report.issues.slice(0, 10).map((issue, index) => (
                    <li key={`${issue.slide}-${index}`}>
                      Slide {issue.slide}: {issue.message}
                    </li>
                  ))}
                </ul>
              )}
              {result.qa_report.slide_images.length > 0 && (
                <div className="slide-grid">
                  {result.qa_report.slide_images.slice(0, 6).map((imagePath) => (
                    <img key={imagePath} src={qaSlideUrl(imagePath)} alt="Slide preview" />
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
