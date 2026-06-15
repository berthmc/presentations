---
name: 500-tech-article-pipeline
description: >-
  End-to-end workflow for generating a tech article: trigger draft, validate quality scorer
  output, generate Imagen images, publish English content to live.
---

# Tech Article Pipeline

**English (EN) only** — no translation step.

## Phase 1 — Trigger Draft
- Trigger draft via backend API (`POST /api/v1/tech-articles/trigger-draft`).

## Phase 2 — Validate Quality Scorer
- Ensure quality scorer output passes thresholds before generating images.
- Quarantine if necessary.

## Phase 3 — Generate Images
- Generate Imagen images: `POST /api/v1/tech-articles/articles/{slug}/generate-images`.

## Phase 4 — Publish-to-Live (EN only)
- Publish English HTML to GCP:
  `POST /api/v1/tech-articles/articles/{slug}/publish-to-live?skip_translation=true`
