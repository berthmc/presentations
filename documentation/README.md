# PPTX Engine — Documentation

Index of project documentation. The original product specification lives under [`briefs/`](briefs/).

| Document | Description |
|----------|-------------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Five-stage pipeline, RAG, vLLM, Docker topology |
| [API_REFERENCE.md](API_REFERENCE.md) | FastAPI REST endpoints and request/response schemas |
| [MCP_INTEGRATION.md](MCP_INTEGRATION.md) | MCP server setup for Cursor and Antigravity |
| [TEMPLATE_LIBRARY_GUIDE.md](TEMPLATE_LIBRARY_GUIDE.md) | Persistent template registry and usage |
| [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Local setup, Docker, Qdrant/vLLM, testing |
| [briefs/architecture.md](briefs/architecture.md) | Original architecture specification (hardware, QA loop) |
| [briefs/SKILL.md](briefs/SKILL.md) | Anthropic PPTX skill reference (QA, editing workflows) |
| [antigravity-mcp.example.json](antigravity-mcp.example.json) | Sample Antigravity MCP config |

## Quick links

- **Run locally:** [DEVELOPMENT_GUIDE.md § Quick start](DEVELOPMENT_GUIDE.md#quick-start)
- **Generate via API:** [API_REFERENCE.md § POST /generate](API_REFERENCE.md#post-generate)
- **Model catalog:** [API_REFERENCE.md § GET /models](API_REFERENCE.md#get-models)
- **Generate via MCP:** [MCP_INTEGRATION.md § Tools](MCP_INTEGRATION.md#tools)
- **Upload a corporate template:** [TEMPLATE_LIBRARY_GUIDE.md](TEMPLATE_LIBRARY_GUIDE.md)
