# MCP Integration

The PPTX Engine exposes a **first-party, self-hosted** MCP server for Cursor and Antigravity. It is not a third-party or Runlayer-managed MCP.

## Transports

| Transport | Use case | How to start |
|-----------|----------|--------------|
| **stdio** | IDE spawns the process locally | `pptx-mcp --transport stdio` |
| **HTTP** | Container or shared API process | MCP mounted at `http://localhost:8090/mcp` |

Both transports expose the **same tools**.

## Cursor

Add to [`.cursor/mcp.json`](../.cursor/mcp.json):

### Stdio (recommended for local dev)

```json
{
  "mcpServers": {
    "pptx": {
      "command": "pptx-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "OLLAMA_HOST": "http://localhost:11434",
        "DATA_DIR": "./data"
      }
    }
  }
}
```

Requires `pip install -e .` so `pptx-mcp` is on PATH.

### HTTP (Docker API running)

```json
{
  "mcpServers": {
    "pptx": {
      "url": "http://localhost:8090/mcp"
    }
  }
}
```

## Antigravity

Copy [antigravity-mcp.example.json](antigravity-mcp.example.json) into your Antigravity MCP settings (`mcp_config.json` or equivalent). Use the same `command`/`args`/`env` block for stdio, or `serverUrl` for HTTP.

## Tools

| Tool | Description |
|------|-------------|
| `list_templates` | List persisted templates (`id`, `name`, `source_type`, `is_default`) |
| `register_template` | Register a `.pptx` or `.md` file from a host path |
| `discover_layout_tool` | Return layout profile JSON for a template path |
| `generate_deck` | Full pipeline; prefer `template_id` over `template_path` |
| `render_qa` | Render existing deck and run visual QA |
| `hardware_diagnostics` | Host RAM/GPU profile and model selection |

### generate_deck parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `brief` | string | Content brief (required) |
| `template_id` | string | Library template id (**preferred**) |
| `template_path` | string | Ad-hoc path on MCP host |
| `mode` | string | `scratch` or `template` |
| `title` | string | Optional deck title |
| `run_qa` | bool | Run visual QA (default `true`) |

**Example agent flow**

1. `list_templates` → pick default or user-specified `template_id`
2. `generate_deck(brief="...", template_id="...", mode="scratch", run_qa=true)`
3. Inspect `output_path` and `qa_report.slide_images` in the JSON response
4. Optionally `render_qa(pptx_path="...")` on an existing file

## Timeouts

Generation (LLM + compile + QA) can take several minutes. For long jobs:

- Prefer the **HTTP** transport against the Docker API (stable process, shared `DATA_DIR` volume).
- Set `run_qa=false` during iterative content drafts; run `render_qa` separately when layout is stable.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `./data` | Template library and output paths |
| `OLLAMA_HOST` | `http://localhost:11434` | Local LLM endpoint |
| `MCP_TRANSPORT` | `stdio` | Default transport when `--transport` omitted |
| `GOOGLE_CLOUD_PROJECT` | — | Enables Gemini fallback when Ollama unavailable |

See [`.env.example`](../.env.example) for the full list.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `pptx-mcp` not found | Run `pip install -e .` from repo root |
| Ollama connection refused | Start Ollama; set `OLLAMA_HOST` |
| Template not found | Call `list_templates` or `register_template` first |
| QA errors in MCP response | Install LibreOffice + poppler on host, or use Docker API image |
