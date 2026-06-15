---
name: 500-article-images-publish
description: >-
  End-to-end workflow for an existing article slug: Imagen 3 images -> publish-to-live (EN only).
---

# Article images and publish to GCP

End-to-end workflow for an **existing** article slug: **Imagen 3 images → publish-to-live** (thecloudarchitect.io or markets.thecloudarchitect.io).

**English (EN) only** — always use `skip_translation=true`. Do not invoke translation endpoints.

This skill does **not** create draft content from pipelines; it assumes the article already exists in Firestore. For automated morning/index briefs, use the `500-morning-briefing` skill instead.

> **Streamlined since April 2026:** Both **markets** and **tech** use a single `publish-to-live` API endpoint. Only the EN article slug HTML and listing surfaces are uploaded to GCS. The HTTP API returns **202 Accepted** and runs the long tail in the background (Pub/Sub or asyncio).

## Prerequisites

- CMS backend at `http://localhost:8001` (`sudo docker compose up -d backend` if needed)
- Known **`slug`** and **domain**: `markets` or `tech`

---

## Automated (primary)

```powershell
.\scripts\article_images_translate_publish.ps1 -Slug "<slug>" -Domain "<markets|tech>" -SkipTranslate
```

The script name is legacy; `-SkipTranslate` enforces EN-only publish.

### Optional flags

| Flag | Effect |
|------|--------|
| `-SkipImages` | Re-use existing hero/supporting images |
| `-SkipTranslate` | **Required** — EN-only publish (no Gemini translation) |
| `-Force` | Override `needs_review` status guard |
| `-BaseUrl <url>` | Custom backend URL (default `http://localhost:8001`) |

### What the script does

1. **Validate** — Fetches article, checks status.
2. **Images** — Calls Imagen 3 endpoint.
3. **Publish** — Calls `publish-to-live?skip_translation=true` for the domain.

---

## Manual (reference)

```powershell
$slug   = "your-article-slug"
$domain = "markets"   # or "tech"
```

### Phase 1 — Validate

```powershell
$article = Invoke-RestMethod "http://localhost:8001/api/v1/domain-articles/$domain/$slug"
$article | Select-Object slug, status, title | Format-List
```

### Phase 2 — Generate images

**Markets:**

```powershell
$images = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/markets/articles/$slug/generate-images?regenerate_prompts=true"
```

**Tech:**

```powershell
$images = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/tech-articles/articles/$slug/generate-images?regenerate_prompts=true"
```

### Phase 3 — Publish EN to live

**Markets:**

```powershell
$pub = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/markets/articles/$slug/publish-to-live?skip_translation=true"
Write-Host "Rendered:  $($pub.render.file_path)"
Write-Host "GCS files: $($pub.gcs_sync.uploaded.Count)"
Write-Host "Live URL:  $($pub.render.url)"
```

**Tech:**

```powershell
$pub = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/tech-articles/articles/$slug/publish-to-live?skip_translation=true"
```

---

## Quick reference — endpoints

| Step | Markets | Tech |
|------|---------|------|
| Fetch | `GET /api/v1/domain-articles/markets/{slug}` | `GET /api/v1/domain-articles/tech/{slug}` |
| Images | `POST /api/v1/markets/articles/{slug}/generate-images` | `POST /api/v1/tech-articles/articles/{slug}/generate-images` |
| **Publish EN** | `POST /api/v1/markets/articles/{slug}/publish-to-live?skip_translation=true` | `POST /api/v1/tech-articles/articles/{slug}/publish-to-live?skip_translation=true` |

Base URL: `http://localhost:8001`.

## Error handling

| Condition | Action |
|-----------|--------|
| Backend down | Start `backend` container; retry |
| Image URLs missing | Retry Phase 2; do not publish until resolved |
| publish-to-live 503 | GCS upload failed; retry |
| publish-to-live 500 | Firestore/sitemap step failed; retry |
