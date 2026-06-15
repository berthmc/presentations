# Presentations@Carmélites

Local-first LLM-powered PowerPoint generation with Material Design 3 styling, template fidelity, and visual QA.

## Features

- **Template-driven generation** via `python-pptx` (corporate `.pptx` themes preserved)
- **From-scratch generation** via `pptxgenjs` with MD3 tokens
- **Persistent template library** with `template_id` across sessions
- **Markdown templates** (`.md`) with layout placeholders
- **Local Ollama** synthesis with **Gemini/Vertex** cloud fallback
- **Visual QA loop**: LibreOffice → PDF → JPEG → VLM + geometric checks
- **Surfaces**: React + Vite MD3 web UI, FastAPI REST, **MCP server** for Cursor and Antigravity

## Documentation

Full docs: **[documentation/README.md](documentation/README.md)**

| Guide | Description |
|-------|-------------|
| [Development](documentation/DEVELOPMENT_GUIDE.md) | Setup, Docker, testing |
| [API Reference](documentation/API_REFERENCE.md) | REST endpoints |
| [Architecture](documentation/SYSTEM_ARCHITECTURE.md) | Pipeline and components |
| [MCP Integration](documentation/MCP_INTEGRATION.md) | Cursor / Antigravity |
| [Template Library](documentation/TEMPLATE_LIBRARY_GUIDE.md) | Upload and reuse templates |

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
docker compose -f presentations/docker-compose.yml up --build
```

- API: http://localhost:8090 (OpenAPI at `/docs`)
- UI: http://localhost:8091

## MCP (Cursor + Antigravity)

Self-hosted first-party MCP server — see [documentation/MCP_INTEGRATION.md](documentation/MCP_INTEGRATION.md).

```json
{
  "mcpServers": {
    "pptx": {
      "command": "pptx-mcp",
      "args": ["--transport", "stdio"],
      "env": { "OLLAMA_HOST": "http://localhost:11434", "DATA_DIR": "./data" }
    }
  }
}
```

## Sample assets

- Template: [templates/sample-deck.md](templates/sample-deck.md)
- Brief: [templates/sample-brief.txt](templates/sample-brief.txt)

## Development

```powershell
pytest
ruff check src tests scripts
```

## Repository

[berthmc/presentations](https://github.com/berthmc/presentations) — default branch `dev`
