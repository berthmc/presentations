# PPTX Engine — API Reference

Base URL (local): `http://localhost:8090`

Interactive docs: `http://localhost:8090/docs` (OpenAPI / Swagger)

The React UI proxies API calls through `/api` (dev: Vite on `:8091`; Docker: nginx on `:8091`).

---

## Health & diagnostics

### GET /health

Returns service status.

**Response**

```json
{ "status": "ok" }
```

### GET /diagnostics

Returns hardware profile and recommended local models.

**Response fields**

| Field | Description |
|-------|-------------|
| `platform` | Host OS |
| `active_profile` | `integrated` or `discrete` |
| `synthesis_model` | Default Ollama model for deck JSON synthesis |
| `vlm_model` | Vision model for QA |
| `total_ram_gb` | Host RAM (Windows only) |
| `integrated_vram_gb` | Integrated GPU VRAM estimate (Windows) |
| `discrete_gpu_detected` | NVIDIA discrete GPU detected |
| `supports_vlm` | Whether local VLM QA is expected to work |

### GET /models

Returns the synthesis model catalog with live availability probes.

**Response**

```json
{
  "default": "auto",
  "models": [
    {
      "id": "qwen2.5:7b",
      "label": "Qwen 2.5 7B (local)",
      "provider": "ollama",
      "recommended_for": "Technical decks, integrated GPUs, source-grounded content",
      "speed": "medium",
      "quality": "good",
      "notes": "Default on integrated profile.",
      "available": true
    }
  ]
}
```

| `provider` | Availability check |
|------------|-------------------|
| `ollama` | Ollama `/api/tags` and model installed |
| `vllm` | vLLM OpenAI `/v1/models` reachable |
| `gemini` | `GOOGLE_CLOUD_PROJECT` configured |

---

## Template library

See [TEMPLATE_LIBRARY_GUIDE.md](TEMPLATE_LIBRARY_GUIDE.md) for behaviour and storage layout.

### GET /templates

List all registered templates (default first).

**Response**

```json
{
  "templates": [
    {
      "id": "abc123...",
      "name": "MD3 Sample Deck",
      "source_type": "md",
      "is_default": true,
      "layout_count": 3,
      "layout_names": ["Title Slide", "Content Slide", "Two Column"],
      "created_at": "2026-06-15T12:00:00Z"
    }
  ]
}
```

### GET /templates/{template_id}

Full template record including cached `layout_profile`.

**Errors:** `404` if template id not found.

### POST /templates

Register a new template (multipart form).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | User-facing label |
| `file` | file | yes | `.pptx` or `.md` template |
| `is_default` | bool | no | Set as default selection |

**Response:** Template summary (same shape as list items).

**Errors:** `400` for unsupported file type or invalid template.

### PATCH /templates/{template_id}/default

Mark a template as the default.

### DELETE /templates/{template_id}

Remove template from library and delete stored files.

**Response:** `{ "deleted": "<template_id>" }`

---

## Layout discovery

### POST /discover-layout

Parse a template file and return a layout profile.

| Parameter | Type | Description |
|-----------|------|-------------|
| `template_path` | string (query) | Path **within `DATA_DIR`** visible to the API process |

The resolved path must stay inside `DATA_DIR`; otherwise `400 Invalid path`.

**Response:** `LayoutProfile` JSON with `layouts`, placeholder `ph_idx` indices, and optional `theme`.

**Errors:** `404` if path does not exist; `400` if path escapes `DATA_DIR`.

---

## Generation

### POST /generate

Run the full five-stage pipeline: Researcher → Profiler → Planner → Assembler → optional Inspector with rollback.

**Request body (JSON)**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `brief` | string | required | Content description for the deck |
| `template_id` | string | null | Library template id (**preferred**) |
| `template_path` | string | null | Ad-hoc filesystem path (legacy) |
| `mode` | `"scratch"` \| `"template"` | `"scratch"` | Compile path |
| `title` | string | null | Deck title override |
| `run_qa` | bool | `true` | Run Inspector validation loop after compile |
| `source_context` | string | null | Optional PDF-derived text for factual grounding (not the brief) |
| `allow_cloud` | bool | `false` | When true, Gemini may be used for synthesis fallback and vision QA |
| `synthesis_model` | string | null | Catalog id: Ollama tag, vLLM id, or Gemini model id |

**Example**

```json
POST /generate
Content-Type: application/json

{
  "brief": "Topic: EU cloud adoption\nAudience: Enterprise architects\nTarget length: 6 slides",
  "source_context": "# Annual report\n\nEU cloud spend rose 12% YoY.",
  "template_id": "abc123...",
  "mode": "scratch",
  "title": "EU Cloud Adoption 2026",
  "run_qa": false,
  "synthesis_model": "qwen2.5:7b",
  "allow_cloud": false
}
```

**Response**

| Field | Description |
|-------|-------------|
| `output_path` | Path to generated `.pptx` on the API host |
| `deck_spec` | Structured slide content used for compile |
| `qa_report` | Inspector result when `run_qa=true` |
| `layout_profile` | Layout metadata used for synthesis |

**Errors:** `400` for validation errors (missing template in template mode, synthesis failure, etc.).

### POST /generate/upload

Multipart variant: same fields as `/generate` plus optional `template` file upload. Uploaded templates are auto-registered in the library.

| Field | Default | Notes |
|-------|---------|-------|
| `run_qa` | `false` | Unlike JSON `/generate`, upload defaults QA off for faster UI uploads |

### POST /ingest/pdf

Extract Markdown from an uploaded PDF for use as `source_context` during generation (grounding reference, not the brief).

**Request:** multipart form with `file` (`.pdf`).

**Response:**

```json
{
  "source_context": "# Report title\n\nExtracted body…",
  "filename": "report.pdf",
  "text": "# Report title\n\nExtracted body…"
}
```

The `text` field is retained for backward compatibility. Extraction uses the PDF Toolbox MCP when configured; see [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md).

---

## QA & downloads

### POST /qa/render

Run visual QA on an existing `.pptx` within `DATA_DIR/output/`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `pptx_path` | string | Path to presentation file under `output/` |

**Errors:** `400` invalid path; `404` file not found; `503` if LibreOffice/poppler unavailable.

### GET /download/{filename}

Download a generated deck from `DATA_DIR/output/`. Filename must not contain `/`, `\`, or `..`.

### GET /qa/slides/{deck_stem}/{image_name}

Serve a JPEG slide image from the QA render cache. Used by the React UI for previews.

Example: `/qa/slides/My_Deck_abc123/slide-01.jpg`

Path segments must not contain `..`.

---

## MCP over HTTP

MCP is mounted at **`/mcp`** on the same port as the API when the container runs with `MCP_TRANSPORT=http`.

See [MCP_INTEGRATION.md](MCP_INTEGRATION.md).

---

## Error codes

| Code | Typical cause |
|------|----------------|
| `400` | Invalid request, path traversal, unsupported template, synthesis/compile error |
| `404` | Template, file, or slide image not found |
| `503` | QA rendering dependencies missing (`soffice`, `pdftoppm`) |
