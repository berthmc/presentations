import { useRef, useState } from "react";
import { downloadUrl, generateDeck, ingestPdf, qaSlideUrl } from "../api/client";
import type { GenerateResult } from "../types";
import { composeBrief, EXAMPLE_BRIEF } from "../utils/brief";
import { ModelSelector } from "./ModelSelector";

function isGeminiModelId(modelId: string): boolean {
  return modelId.startsWith("gemini");
}

type SourceDoc = { filename: string; text: string };

function mergeSourceDocuments(docs: SourceDoc[]): string {
  return docs.map((doc) => `--- Document: ${doc.filename} ---\n${doc.text}`).join("\n\n");
}

interface Props {
  templateId: string;
  mode: "scratch" | "template";
  onModeChange: (mode: "scratch" | "template") => void;
  onResult: (result: GenerateResult | null) => void;
}

export function GenerateForm({ templateId, mode, onModeChange, onResult }: Props) {
  const [title, setTitle] = useState("");
  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("");
  const [goal, setGoal] = useState("");
  const [tone, setTone] = useState("");
  const [slideCount, setSlideCount] = useState("");
  const [keyPoints, setKeyPoints] = useState("");
  const [sourceDocs, setSourceDocs] = useState<SourceDoc[]>([]);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [synthesisModel, setSynthesisModel] = useState("auto");
  const [allowCloud, setAllowCloud] = useState(false);
  const [runQa, setRunQa] = useState(false);
  const [status, setStatus] = useState("");
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [ingestingCount, setIngestingCount] = useState(0);
  const pdfInputRef = useRef<HTMLInputElement>(null);

  const ingesting = ingestingCount > 0;

  function loadExampleBrief() {
    setTopic(EXAMPLE_BRIEF.topic);
    setAudience(EXAMPLE_BRIEF.audience);
    setGoal(EXAMPLE_BRIEF.goal);
    setTone(EXAMPLE_BRIEF.tone);
    setSlideCount(EXAMPLE_BRIEF.slideCount);
    setKeyPoints(EXAMPLE_BRIEF.keyPoints);
    setStatus("Loaded example brief.");
  }

  function clearSourceDocuments() {
    setSourceDocs([]);
    setPreviewIndex(null);
    setStatus("Source documents removed.");
  }

  function removeSourceDocument(index: number) {
    setSourceDocs((prev) => prev.filter((_, docIndex) => docIndex !== index));
    setPreviewIndex((prev) => {
      if (prev === null) {
        return null;
      }
      if (prev === index) {
        return null;
      }
      if (prev > index) {
        return prev - 1;
      }
      return prev;
    });
    setStatus("Source document removed.");
  }

  function toggleSourcePreview(index: number) {
    setPreviewIndex((prev) => (prev === index ? null : index));
  }

  function handleSynthesisModelChange(modelId: string) {
    setSynthesisModel(modelId);
    if (isGeminiModelId(modelId)) {
      setAllowCloud(true);
    }
  }

  const geminiModelSelected = synthesisModel !== "auto" && isGeminiModelId(synthesisModel);

  async function handlePdfUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    event.target.value = "";
    if (!files || files.length === 0) {
      return;
    }

    const fileList = Array.from(files);
    setIngestingCount((count) => count + fileList.length);
    setStatus(`Extracting ${fileList.length} PDF${fileList.length > 1 ? "s" : ""}…`);

    try {
      const results = await Promise.all(
        fileList.map(async (file) => {
          try {
            const { source_context, filename } = await ingestPdf(file);
            return { filename: filename ?? file.name, text: source_context };
          } finally {
            setIngestingCount((count) => count - 1);
          }
        }),
      );
      setSourceDocs((prev) => [...prev, ...results]);
      setPreviewIndex(null);
      const names = results.map((doc) => doc.filename).join(", ");
      setStatus(`Attached source document${results.length > 1 ? "s" : ""}: ${names}`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "PDF extraction failed");
    }
  }

  async function handleGenerate() {
    if (!topic.trim()) {
      setStatus("Enter a topic or details for the presentation.");
      return;
    }
    const brief = composeBrief({
      topic,
      audience,
      goal,
      tone,
      slideCount,
      keyPoints,
    });
    const sourceContext = sourceDocs.length ? mergeSourceDocuments(sourceDocs) : undefined;
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
        synthesis_model: synthesisModel === "auto" ? undefined : synthesisModel,
        source_context: sourceContext,
        allow_cloud: allowCloud,
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
      <p className="brief-guidance">
        Describe your presentation using the fields below. Provide at least a topic; audience, goal, tone, target
        length, and key points help the model structure slides appropriately. This is a content brief, not a
        per-slide design script. Optionally attach PDFs as source documents for factual grounding.
      </p>
      <button type="button" className="text-link" onClick={loadExampleBrief}>
        Load example brief
      </button>
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
      <ModelSelector value={synthesisModel} onChange={handleSynthesisModelChange} allowCloud={allowCloud} />
      <div className="field">
        <label htmlFor="topic">Topic / details</label>
        <textarea
          id="topic"
          className="textarea-md"
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          placeholder="Main subject and any context the model should know…"
        />
      </div>
      <div className="field">
        <label>Source documents (optional)</label>
        <p className="field-hint">
          Upload one or more PDFs to ground slide content in source facts. The extracted text is not used as the brief.
        </p>
        <input
          ref={pdfInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          hidden
          onChange={handlePdfUpload}
        />
        <div className="source-doc-row">
          <button
            type="button"
            className="outline"
            onClick={() => pdfInputRef.current?.click()}
            disabled={busy || ingesting}
          >
            {ingesting ? `Extracting PDF${ingestingCount > 1 ? "s" : ""}…` : "Upload PDFs"}
          </button>
          {sourceDocs.length > 0 && (
            <button type="button" className="text-link" onClick={clearSourceDocuments} disabled={busy || ingesting}>
              Remove all
            </button>
          )}
        </div>
        {sourceDocs.length > 0 && (
          <div className="source-doc-row">
            {sourceDocs.map((doc, index) => (
              <span key={`${doc.filename}-${index}`} className="source-chip">
                {doc.filename} · {doc.text.length.toLocaleString()} chars
                <button type="button" className="text-link" onClick={() => toggleSourcePreview(index)}>
                  {previewIndex === index ? "Hide preview" : "Preview"}
                </button>
                <button type="button" className="text-link" onClick={() => removeSourceDocument(index)}>
                  Remove
                </button>
              </span>
            ))}
          </div>
        )}
        {previewIndex !== null && sourceDocs[previewIndex] && (
          <pre className="source-preview">
            {sourceDocs[previewIndex].text.slice(0, 500)}
            {sourceDocs[previewIndex].text.length > 500 ? "…" : ""}
          </pre>
        )}
      </div>
      <div className="field-grid">
        <div className="field">
          <label htmlFor="audience">Audience</label>
          <input
            id="audience"
            value={audience}
            onChange={(event) => setAudience(event.target.value)}
            placeholder="e.g. EU retail investors"
          />
        </div>
        <div className="field">
          <label htmlFor="goal">Goal</label>
          <input
            id="goal"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="e.g. Explain regulatory impact"
          />
        </div>
        <div className="field">
          <label htmlFor="tone">Tone</label>
          <input
            id="tone"
            value={tone}
            onChange={(event) => setTone(event.target.value)}
            placeholder="e.g. Professional, objective"
          />
        </div>
        <div className="field">
          <label htmlFor="slide-count">Target length (slides)</label>
          <input
            id="slide-count"
            type="number"
            min={1}
            max={50}
            value={slideCount}
            onChange={(event) => setSlideCount(event.target.value)}
            placeholder="e.g. 8"
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="key-points">Key points</label>
        <textarea
          id="key-points"
          className="textarea-sm"
          value={keyPoints}
          onChange={(event) => setKeyPoints(event.target.value)}
          placeholder="One point per line…"
        />
      </div>
      <div className="checkbox-row">
        <input id="run-qa" type="checkbox" checked={runQa} onChange={(event) => setRunQa(event.target.checked)} />
        <label htmlFor="run-qa">Run visual QA</label>
      </div>
      <div className="checkbox-row">
        <input
          id="allow-cloud"
          type="checkbox"
          checked={allowCloud}
          disabled={geminiModelSelected}
          onChange={(event) => setAllowCloud(event.target.checked)}
        />
        <label htmlFor="allow-cloud">
          Allow Gemini (cloud AI) — your brief and source documents will be sent to Google Vertex AI
        </label>
      </div>
      {geminiModelSelected && (
        <p className="field-hint">A Gemini model is selected; cloud AI is required for synthesis.</p>
      )}
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
