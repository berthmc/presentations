import { useRef, useState, type ChangeEvent } from "react";
import { downloadUrl, generateDeck, ingestPdf, qaSlideUrl } from "../api/client";
import type { GenerateResult } from "../types";
import { composeBrief, EXAMPLE_BRIEF } from "../utils/brief";
import { ModelSelector } from "./ModelSelector";
import { TextField } from "./TextField";

function isGeminiModelId(modelId: string): boolean {
  return modelId.startsWith("gemini");
}

type SourceDoc = { filename: string; text: string };

function mergeSourceDocuments(docs: SourceDoc[]): string {
  return docs.map((doc) => `--- Document: ${doc.filename} ---\n${doc.text}`).join("\n\n");
}

interface Props {
  templateId: string;
  templateSourceType: string | null;
  mode: "scratch" | "template";
  onModeChange: (mode: "scratch" | "template") => void;
  onResult: (result: GenerateResult | null) => void;
}

export function GenerateForm({ templateId, templateSourceType, mode, onModeChange, onResult }: Props) {
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
    if (mode === "template") {
      if (!templateId) {
        setStatus("Select a .pptx template on the Templates tab before using Template mode.");
        return;
      }
      if (templateSourceType !== "pptx") {
        setStatus("Template mode requires a .pptx library template. Choose one on the Templates tab.");
        return;
      }
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
    setStatus("Queued…");
    setResult(null);
    onResult(null);
    try {
      const payload = await generateDeck(
        {
          brief,
          mode,
          title: title || undefined,
          run_qa: runQa,
          template_id: templateId || null,
          synthesis_model: synthesisModel === "auto" ? undefined : synthesisModel,
          source_context: sourceContext,
          allow_cloud: allowCloud,
        },
        (message) => setStatus(message),
      );
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
      <header className="section-header">
        <h2>Generate Presentation</h2>
        <button type="button" className="text" onClick={loadExampleBrief}>
          Load example brief
        </button>
      </header>

      <div className="callout">
        <span className="chip chip--assist">Content brief</span>
        <p>
          Describe your presentation using the fields below. Provide at least a topic; audience, goal, tone, target
          length, and key points help the model structure slides appropriately. Optionally attach PDFs as source
          documents for factual grounding.
        </p>
      </div>

      <TextField id="title" label="Title" value={title} onChange={(event: ChangeEvent<HTMLInputElement>) => setTitle(event.target.value)} />

      <div className="text-field">
        <span className="text-field__label" style={{ position: "static", marginBottom: "0.5rem" }}>
          Mode
        </span>
        <div className="segmented-button" role="group" aria-label="Generation mode">
          <button
            type="button"
            className="segmented-button__option"
            aria-pressed={mode === "scratch"}
            onClick={() => onModeChange("scratch")}
          >
            Scratch
          </button>
          <button
            type="button"
            className="segmented-button__option"
            aria-pressed={mode === "template"}
            onClick={() => {
              if (!templateId || templateSourceType !== "pptx") {
                setStatus("Template mode requires a .pptx library template. Select one on the Templates tab.");
                return;
              }
              onModeChange("template");
            }}
          >
            Template
          </button>
        </div>
      </div>

      <ModelSelector value={synthesisModel} onChange={handleSynthesisModelChange} allowCloud={allowCloud} />

      <TextField
        id="topic"
        label="Topic / details"
        multiline
        className="textarea-md"
        value={topic}
        onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setTopic(event.target.value)}
      />

      <div className="text-field">
        <span className="text-field__label" style={{ position: "static", marginBottom: "0.5rem" }}>
          Source documents (optional)
        </span>
        <p className="text-field__hint" style={{ margin: "0 0 0.5rem" }}>
          Upload one or more PDFs to ground slide content in source facts.
        </p>
        <input
          ref={pdfInputRef}
          type="file"
          className="hidden-input"
          accept=".pdf,application/pdf"
          multiple
          onChange={handlePdfUpload}
        />
        <div className="source-doc-row">
          <button
            type="button"
            className="tonal btn-with-icon"
            onClick={() => pdfInputRef.current?.click()}
            disabled={busy || ingesting}
          >
            <span className="material-symbols-rounded">picture_as_pdf</span>
            {ingesting ? `Extracting PDF${ingestingCount > 1 ? "s" : ""}…` : "Upload PDFs"}
          </button>
          {sourceDocs.length > 0 && (
            <button type="button" className="text" onClick={clearSourceDocuments} disabled={busy || ingesting}>
              Remove all
            </button>
          )}
        </div>
        {sourceDocs.length > 0 && (
          <div className="chip-row" style={{ marginTop: "0.75rem" }}>
            {sourceDocs.map((doc, index) => (
              <span key={`${doc.filename}-${index}`} className="chip chip--input">
                {doc.filename} · {doc.text.length.toLocaleString()} chars
                <button
                  type="button"
                  className="chip__dismiss"
                  aria-label={`Preview ${doc.filename}`}
                  onClick={() => toggleSourcePreview(index)}
                >
                  <span className="material-symbols-rounded">
                    {previewIndex === index ? "visibility_off" : "visibility"}
                  </span>
                </button>
                <button
                  type="button"
                  className="chip__dismiss"
                  aria-label={`Remove ${doc.filename}`}
                  onClick={() => removeSourceDocument(index)}
                >
                  <span className="material-symbols-rounded">close</span>
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
        <TextField
          id="audience"
          label="Audience"
          value={audience}
          onChange={(event: ChangeEvent<HTMLInputElement>) => setAudience(event.target.value)}
        />
        <TextField id="goal" label="Goal" value={goal} onChange={(event: ChangeEvent<HTMLInputElement>) => setGoal(event.target.value)} />
        <TextField id="tone" label="Tone" value={tone} onChange={(event: ChangeEvent<HTMLInputElement>) => setTone(event.target.value)} />
        <TextField
          id="slide-count"
          label="Target length (slides)"
          type="number"
          min={1}
          max={50}
          value={slideCount}
          onChange={(event: ChangeEvent<HTMLInputElement>) => setSlideCount(event.target.value)}
        />
      </div>

      <TextField
        id="key-points"
        label="Key points"
        multiline
        value={keyPoints}
        onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setKeyPoints(event.target.value)}
      />

      <div className="text-field">
        <span className="text-field__label" style={{ position: "static", marginBottom: "0.5rem" }}>
          Options
        </span>
        <div className="segmented-button" role="group" aria-label="Generation options">
          <button
            type="button"
            className="segmented-button__option"
            aria-pressed={runQa}
            onClick={() => setRunQa((value) => !value)}
          >
            Visual QA
          </button>
          <button
            type="button"
            className="segmented-button__option"
            aria-pressed={allowCloud || geminiModelSelected}
            disabled={geminiModelSelected}
            onClick={() => setAllowCloud((value) => !value)}
          >
            Cloud AI
          </button>
        </div>
        {geminiModelSelected && (
          <p className="text-field__hint">A Gemini model is selected; cloud AI is required for synthesis.</p>
        )}
        {!geminiModelSelected && allowCloud && (
          <p className="text-field__hint">
            Your brief and source documents will be sent to Google Vertex AI when using Gemini.
          </p>
        )}
      </div>

      <button type="button" className="primary extended-fab" onClick={handleGenerate} disabled={busy}>
        <span className="material-symbols-rounded">rocket_launch</span>
        {busy ? "Generating…" : "Generate presentation"}
      </button>

      {busy && (
        <div className="linear-progress" role="progressbar" aria-label="Generating presentation">
          <div className="linear-progress__bar" />
        </div>
      )}

      <p className={`status${status.startsWith("Error") || status.includes("failed") ? " error" : ""}`}>{status}</p>

      {result && (
        <section className="md3-card md3-card--success" style={{ marginTop: "1.25rem" }}>
          <h3 style={{ margin: "0 0 0.75rem", fontSize: "var(--md-sys-typescale-title-medium-size)" }}>
            Generation complete
          </h3>
          <a className="download-link" href={downloadUrl(result.output_path)}>
            <span className="material-symbols-rounded">download</span>
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
        </section>
      )}
    </section>
  );
}
