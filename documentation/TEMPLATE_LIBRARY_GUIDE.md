# Template Library Guide

The template library persists corporate `.pptx` themes and markdown layout templates across sessions. Templates are **not** converted to markdown for compile fidelity — the original binary (or `.md` spec) is kept on disk.

## Overview

| Concept | Description |
|---------|-------------|
| **Template record** | Metadata + cached layout profile in `registry.json` |
| **Template file** | Stored copy at `data/templates/{id}/template.pptx` or `template.md` |
| **Layout profile** | JSON map of `layout_index` → placeholder `ph_idx` names (cached at upload) |
| **Default template** | Pre-selected in UI and listed first in API/MCP |

On first startup, the engine seeds **MD3 Sample Deck** from [`templates/sample-deck.md`](../templates/sample-deck.md) if the library is empty.

## Supported formats

| Format | `source_type` | Generation mode |
|--------|---------------|-----------------|
| `.pptx` | `pptx` | `template` — fills slide master placeholders |
| `.md` | `md` | `scratch` — guides layout indices for pptxgenjs |

## Register a template

### React UI

1. Open `http://localhost:8091`
2. Enter a **Template name**
3. Upload `.pptx` or `.md`
4. Optionally check **Set as default**

### REST API

```powershell
curl -X POST http://localhost:8090/templates `
  -F "name=Acme Corporate 2026" `
  -F "is_default=true" `
  -F "file=@C:\path\to\corporate.pptx"
```

### MCP

```
register_template(name="Acme Corporate 2026", template_path="C:/path/to/corporate.pptx", is_default=true)
```

Returns JSON including `template_id`.

## Generate with a saved template

Prefer **`template_id`** over raw filesystem paths.

```json
POST /generate
{
  "brief": "Q3 pipeline milestones for EU enterprise clients.",
  "template_id": "abc123...",
  "mode": "template",
  "run_qa": false
}
```

For `.pptx` templates, set `mode` to `template`. For `.md` templates, `scratch` is typical (layout profile guides slide indices).

## Markdown template format

```markdown
---
theme: tech
title: Corporate Deck
---

## slide: Title Slide
- ph_idx: 0 | title
- ph_idx: 1 | subtitle

## slide: Content Slide
- ph_idx: 0 | section_title
- ph_idx: 1 | body
```

See [`templates/sample-deck.md`](../templates/sample-deck.md).

## What the LLM receives

The synthesis step receives the **cached layout profile JSON** (indices and placeholder names), not a markdown conversion of a `.pptx`. Optional markitdown/thumbnail analysis (per Anthropic skill docs) can supplement layout choice but does not replace the template file at compile time.

## Manage templates

| Action | REST | MCP |
|--------|------|-----|
| List | `GET /templates` | `list_templates` |
| Detail | `GET /templates/{id}` | — |
| Set default | `PATCH /templates/{id}/default` | Re-register with `is_default=true` |
| Delete | `DELETE /templates/{id}` | — |

## Storage layout

```
data/templates/
  registry.json
  a1b2c3d4.../
    template.pptx
  e5f6g7h8.../
    template.md
```

`registry.json` holds serialized `TemplateRecord` objects including embedded `layout_profile`.

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Template mode fails | `.md` template with `mode=template` | Use `mode=scratch` for `.md`, or upload a `.pptx` |
| Layout mismatch | LLM picked invalid `layout_index` | Re-upload after fixing master slides; check `GET /templates/{id}` |
| Missing after restart | Different `DATA_DIR` | Use consistent `.env` / Docker volume |

See [API_REFERENCE.md](API_REFERENCE.md) for endpoint details.
