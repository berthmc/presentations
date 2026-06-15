# Development Guide

How to run, test, and troubleshoot Presentations@Carmélites locally and in Docker.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.11 | API, MCP, pipeline |
| Node.js | ≥ 20 | React UI; pptxgenjs scratch builder |
| Ollama | latest | Local LLM (optional; Gemini fallback available) |
| LibreOffice | headless | Visual QA rendering |
| poppler-utils | `pdftoppm` | QA slide rasterization |

## Quick start

```powershell
# 1. Environment
Copy-Item .env.example .env

# 2. Python backend
pip install -e ".[dev]"
cd src/presentations/compile/node; npm install; cd ../../../..

# 3. React UI
cd frontend; npm install; cd ..

# 4. Run (two terminals)
pptx-api                    # http://localhost:8090
cd frontend; npm run dev    # http://localhost:8091  (proxies /api → :8090)
```

Optional: start Ollama and pull models:

```powershell
ollama pull qwen2.5:3b
ollama pull qwen2.5vl:7b   # optional, for VLM QA on discrete GPU profile
```

## Docker

```powershell
docker compose -f presentations/docker-compose.yml up --build
```

If you still have containers from the old **`docker`** project (before the folder rename), tear them down by project name — the old compose path no longer exists:

```powershell
docker compose -p docker down -v
```

| URL | Service |
|-----|---------|
| http://localhost:8090 | API + MCP at `/mcp` |
| http://localhost:8091 | React UI (nginx, `/api` proxy) |

Data persists in Docker volume `presentations_pptx-data` at `/data`.

### Container commands

```powershell
docker compose -f presentations/docker-compose.yml logs -f pptx-api
docker compose -f presentations/docker-compose.yml exec pptx-api pptx-mcp --transport stdio
```

## Environment variables

Copy from [`.env.example`](../.env.example). Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `./data` | All runtime data |
| `API_PORT` | `8090` | FastAPI listen port |
| `OLLAMA_HOST` | `http://localhost:11434` | Local LLM |
| `OLLAMA_NUM_PREDICT` | `4096` | Max output tokens for Ollama synthesis |
| `OLLAMA_NUM_CTX` | `16384` | Ollama context window (`num_ctx`); raise if prompts overflow |
| `OLLAMA_TEMPERATURE` | `0.1` | Ollama synthesis temperature |
| `OLLAMA_MAX_SOURCE_CONTEXT_CHARS` | `4000` | Max PDF source text chars in Ollama prompts (Gemini uncapped) |
| `ALLOW_CLOUD_LLM_DEFAULT` | `false` | Operator default for cloud LLM; users opt in per-request via UI `allow_cloud` |
| `HARDWARE_PROFILE` | `auto` | `integrated`, `discrete`, or `auto` |
| `QA_MAX_ITERATIONS` | `3` | Visual QA retry limit |
| `GOOGLE_CLOUD_PROJECT` | — | Gemini/Vertex fallback |
| `PDF_MCP_URL` | `http://localhost:3005/mcp` | PDF Toolbox MCP for source document extraction |
| `PDF_MCP_WORKSPACE_DIR` | `../pdf/mcp-workspace` | Shared workspace for staged PDF uploads |

PDF source document ingestion requires the [PDF Toolbox](https://github.com/berthmc/pdf) MCP service on port 3005. Upload a PDF in the UI (or call `POST /ingest/pdf`), then generate with both a **brief** (presentation intent) and optional **`source_context`** (extracted PDF text for factual grounding). In Docker, `presentations/docker-compose.yml` bind-mounts `../../pdf/mcp-workspace` (sibling repo) to `/pdf-mcp-workspace` so staged PDFs are visible to the PDF MCP container.

Frontend (Vite): see [`frontend/.env.example`](../frontend/.env.example). Default dev setup uses `/api` proxy — no env file required.

## Testing

```powershell
pytest
ruff check src tests scripts
cd frontend; npm run build
```

| Suite | Location | Covers |
|-------|----------|--------|
| Unit | `tests/test_*.py` | Schemas, theme, registry, profiles |
| Smoke | `tests/test_smoke_compile.py` | pptxgenjs scratch compile |
| E2E API | `tests/test_e2e_api.py` | Templates, generate, QA images |

## Console entry points

| Command | Description |
|---------|-------------|
| `pptx-api` | Start FastAPI server |
| `pptx-mcp` | Start MCP server (`--transport stdio\|http`) |

## Project layout

```
pptx/
  frontend/              React + Vite UI
  src/presentations/     Python package
  presentations/         Dockerfile, compose, nginx
  documentation/         Project docs (this folder)
  documentation/briefs/  Original specs & Anthropic skill refs
  scripts/office/        PPTX unpack/pack utilities
  templates/             Sample .md template + brief
  tests/
```

## Hardware diagnostics

```powershell
.\scripts\profile_diag.ps1
Invoke-RestMethod http://localhost:8090/diagnostics
```

## Troubleshooting

### API starts but generation fails

- Confirm Ollama is running: `ollama list`
- Check logs: `docker compose -f presentations/docker-compose.yml logs pptx-api`
- By default, generation uses **local Ollama only**. Enable **Allow Gemini (cloud AI)** in the UI to permit Vertex AI fallback when Ollama fails or is unavailable.
- Set `GOOGLE_CLOUD_PROJECT` and credentials when using cloud AI.
- In Docker with a discrete GPU host, set `HARDWARE_PROFILE=discrete` in `.env` to use `deepseek-r1:14b` instead of `qwen2.5:3b`
- Selecting a Gemini model in the synthesis dropdown implicitly enables cloud AI for synthesis.

### Visual QA skipped

- Install LibreOffice (`soffice`) and poppler (`pdftoppm`)
- In Docker, these are included in `pptx-api` image
- QA failure returns `503` on `/qa/render`; generation with `run_qa=false` still works

### React UI cannot reach API

- Ensure `pptx-api` is running on `:8090`
- Vite dev server proxies `/api` — do not set `VITE_API_BASE_URL` unless calling API directly
- In Docker, use `http://localhost:8091` (nginx handles proxy)

### pptxgenjs compile fails

```powershell
cd src/presentations/compile/node; npm install
node builder.mjs   # expects JSON on stdin
```

### Template library empty in tests

Tests isolate `DATA_DIR` via `monkeypatch`. Production library lives in `./data/templates/`.

## Related documentation

- [API_REFERENCE.md](API_REFERENCE.md)
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md)
- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
- [briefs/architecture.md](briefs/architecture.md)
