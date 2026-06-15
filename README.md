# PPTX Generation Engine

Local-first LLM-powered PowerPoint generation with Material Design 3 styling, template fidelity, and visual QA.

## Features

- **Template-driven generation** via `python-pptx` (corporate `.pptx` themes preserved)
- **From-scratch generation** via `pptxgenjs` with MD3 tokens
- **Markdown templates** (`.md`) with layout placeholders
- **Local Ollama** synthesis with **Gemini/Vertex** cloud fallback
- **Visual QA loop**: LibreOffice → PDF → JPEG → VLM + geometric checks
- **Surfaces**: React + Vite MD3 web UI, FastAPI REST, **MCP server** for Cursor and Antigravity

## Quick start

```powershell
Copy-Item .env.example .env
pip install -e ".[dev]"
cd src/presentations/compile/node; npm install; cd ../../../..
cd frontend; npm install; cd ..

# Terminal 1 — API
pptx-api    # http://localhost:8090

# Terminal 2 — React UI (proxies /api -> :8090)
cd frontend; npm run dev    # http://localhost:8091
```

### Docker

```powershell
docker compose -f docker/docker-compose.yml up --build
```

## MCP (Cursor + Antigravity)

Self-hosted first-party MCP server — not a third-party/shadow MCP.

### Stdio (IDE-spawned)

```json
{
  "mcpServers": {
    "pptx": {
      "command": "pptx-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "OLLAMA_HOST": "http://localhost:11434"
      }
    }
  }
}
```

### HTTP (container)

```json
{
  "mcpServers": {
    "pptx": {
      "url": "http://localhost:8090/mcp"
    }
  }
}
```

### Tools

| Tool | Description |
|------|-------------|
| `list_templates` | List persisted templates (id, name, source_type, is_default) |
| `register_template` | Add a .pptx/.md file to the template library |
| `discover_layout_tool` | Parse `.pptx` or `.md` template layouts |
| `generate_deck` | Full pipeline; pass `template_id` (preferred) or `template_path` |
| `render_qa` | Render existing deck and run visual QA |
| `hardware_diagnostics` | Host RAM/GPU profile and model selection |

## Template library

Templates are persisted under `DATA_DIR/templates/` with a `registry.json` index. Upload once via the UI or `POST /templates`; select by `template_id` on later runs.

| Endpoint | Description |
|----------|-------------|
| `GET /templates` | List saved templates |
| `POST /templates` | Upload and register (multipart: `name`, `file`, optional `is_default`) |
| `GET /templates/{id}` | Full template metadata + cached layout profile |
| `PATCH /templates/{id}/default` | Set default template |
| `DELETE /templates/{id}` | Remove from library |

Generate with a saved template:

```json
POST /generate
{
  "brief": "...",
  "template_id": "abc123...",
  "mode": "template",
  "run_qa": false
}
```

## Architecture

See [documentation/briefs/architecture.md](documentation/briefs/architecture.md).

## Sample assets

- Template: [templates/sample-deck.md](templates/sample-deck.md)
- Brief: [templates/sample-brief.txt](templates/sample-brief.txt)

## Hardware profiles

| Profile | Synthesis | VLM |
|---------|-----------|-----|
| Integrated (Radeon 780M) | `qwen2.5:3b` | optional |
| Discrete (RTX 5070 Ti) | `deepseek-r1:14b` | `qwen2.5-vl:7b` |

Run diagnostics:

```powershell
.\scripts\profile_diag.ps1
curl http://localhost:8090/diagnostics
```

## Development

```powershell
pytest
ruff check src tests
```

## Repository

Version control: [berthmc/presentations](https://github.com/berthmc/presentations)
