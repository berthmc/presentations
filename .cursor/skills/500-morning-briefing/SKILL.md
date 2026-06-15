---
name: 500-morning-briefing
description: >-
  End-to-end workflow for generating a Market Morning Brief or Index Daily Brief
  on markets.thecloudarchitect.io: launches the content pipeline, validates the
  generated article, creates hero and supporting images with Imagen 3, and publishes
  English content to GCP. Use when the user says "/morning-briefing",
  "/index-daily-brief", or asks to generate, run, or publish a morning brief or
  index daily brief.
---

# Morning Briefing / Index Daily Brief

Full automation for generating and publishing `market_morning_brief` and `index_daily_brief` articles on the markets CMS. **English (EN) only** — no translation step.

## Slash Commands

| Command | Article type |
|---------|-------------|
| `/morning-briefing` | `market_morning_brief` — pre-market overview |
| `/index-daily-brief <index_id>` | `index_daily_brief` — per-benchmark brief |

If no `index_id` is given for `/index-daily-brief`, list available indexes first (see Phase 1).

## Prerequisites

- CMS backend running at `http://localhost:8001` (`cms-backend` Docker container)
- `gcloud` authenticated against project `portfoliodashboard-480017`

```powershell
docker ps --filter "name=cms-backend" --format "{{.Names}} {{.Status}}"
```

If not running: `sudo docker compose up -d backend`

---

## Phase 1 — Pipeline Launch

### Morning brief

```powershell
# Optional: pre-warm Tavily market headline cache (~30 s, reduces pipeline latency)
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/markets/tavily/prefetch-morning-brief" `
  -ContentType "application/json" `
  -Body '{}'

# Launch pipeline
$draft = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/markets/trigger-draft" `
  -ContentType "application/json" `
  -Body '{"article_type": "market_morning_brief"}'
$slug = $draft.article_slug
Write-Host "Slug: $slug"
```

### Index daily brief

```powershell
# List available indexes (if index_id unknown)
$indexes = Invoke-RestMethod "http://localhost:8001/api/v1/markets/indexes"
$indexes | Select-Object index_id, name | Format-Table

# Launch pipeline — replace <index_id> with the chosen value (e.g. "sp500")
$draft = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/markets/trigger-draft" `
  -ContentType "application/json" `
  -Body '{"article_type": "index_daily_brief", "index_id": "<index_id>"}'
$slug = $draft.article_slug
Write-Host "Slug: $slug"
```

### Duplicate detection

If the response contains `"duplicate_skipped": true`, an identical brief was already generated today. Report the `existing_slug` to the user and **stop**.

---

## Phase 2 — Output Validation

```powershell
$article = Invoke-RestMethod "http://localhost:8001/api/v1/domain-articles/markets/$slug"
$article | Select-Object slug, status, title | Format-List
```

### Status checks

| Status | Action |
|--------|--------|
| `draft` | Proceed |
| `validated` | Proceed |
| `needs_review` | Warn user; offer `/fix-markets-article-quality <slug>` before continuing |
| Anything else | Report as error and stop |

### Content checks

- `content` field non-empty and at least 400 characters
- `title` and `excerpt` present and non-empty
- `seo_data` object present
- `pipeline_metadata.quality_gate` — if present and fired, surface the signals to the user

---

## Phase 3 — Image Generation

```powershell
$images = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/markets/articles/$slug/generate-images?regenerate_prompts=true"
$images | Select-Object featured_image, supporting_image_url | Format-List
```

Verify both `featured_image` and `supporting_image_url` are non-empty before Phase 4.

---

## Phase 4 — Render EN, Sync to GCS, and Publish

Renders English HTML only (`skip_translation=true`), uploads the slug to GCS, flips `pending_publish` → `published`, regenerates sitemaps, and invalidates Cloud CDN.

```powershell
$publish = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/api/v1/markets/articles/$slug/publish-to-live?skip_translation=true"
Write-Host "GCS sync: $($publish.gcs_sync.success)  |  Deployed: $($publish.deploy.deployed_count)"
$publish | Select-Object gcs_sync, deploy, cdn | Format-List
```

### Response checks

| Field | Expected | Action if wrong |
|-------|----------|-----------------|
| `gcs_sync.success` | `true` | Retry Phase 4 |
| `deploy.deployed_count` | `> 0` | Re-run if GCS succeeded |
| `cdn` | no `error` key | Warn user; propagation may be delayed |

---

## Completion Report

| Phase | Outcome |
|-------|---------|
| Pipeline | Slug generated (or duplicate skipped) |
| Validation | Status, quality signals |
| Images | `featured_image` and `supporting_image_url` URLs |
| Publish | GCS sync OK, deployed count, CDN invalidated, live URL |

## Key API Endpoints

| Step | Endpoint |
|------|----------|
| Tavily pre-warm | `POST /api/v1/markets/tavily/prefetch-morning-brief` |
| List indexes | `GET /api/v1/markets/indexes` |
| Launch pipeline | `POST /api/v1/markets/trigger-draft` |
| Fetch article | `GET /api/v1/domain-articles/markets/{slug}` |
| Generate images | `POST /api/v1/markets/articles/{slug}/generate-images` |
| Publish EN to live | `POST /api/v1/markets/articles/{slug}/publish-to-live?skip_translation=true` |

All calls target `http://localhost:8001`.
