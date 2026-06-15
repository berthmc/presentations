---
name: 700-publish-gcp
description: >-
  GCP-native publishing — Cloud Run renders HTML to GCS from Firestore; drain job promotes
  pending_publish, syncs stubs/sitemaps, and invalidates CDN.
---

# Publish to GCP (Cloud Run pipeline)

When the user says **`/publish-to-gcp`**, **`/publish`**, or follows the agent workflow, use this **GCP-native** path.
Live HTML/CSS is produced **inside Cloud Run** (`cms-backend`) and written to GCS — **not** by uploading the local `website/` tree with `gsutil rsync`.

**English (EN) only**: always pass `skip_translation=true` on per-slug publish calls.

## Prerequisites
- `gcloud` authenticated to project **`portfoliodashboard-480017`**.
- GitHub Actions WIF for workflows that call Cloud Run with OIDC.

## What runs where
- **Cloud Scheduler** -> HTTPS to **`cms-backend`** (Cloud Run, region **`europe-west1`**).
- **Article HTML** -> `article_publishing_service` -> `gcs_article_sync_service`.
- **Sitemaps** -> `gcs_sitemap_sync_service`.
- **Redirect stubs** -> `gcs_stubs_sync_service`.
- **One-shot drain** -> `POST /scheduler/drain-pending-publish`.

## Manual one-shot drain

```powershell
cd C:\dev\cms
gh workflow run drain-pending-publish.yml
```

Or via Cloud Run:

```powershell
$CMS_URL = gcloud run services describe cms-backend --region=europe-west1 --format='value(status.url)'
$TOKEN   = gcloud auth print-identity-token --audiences="$CMS_URL"
Invoke-RestMethod -Method Post -Uri "$CMS_URL/scheduler/drain-pending-publish" -Headers @{ Authorization = "Bearer $TOKEN" }
```

## Ship template/CSS changes
After changing **Jinja templates** or **shared CSS**, re-render published slugs with `skip_translation=true` and `skip_images=True` where supported, then run the drain.

## Deprecated — local `gsutil rsync`
Use **only if Cloud Run is unavailable**:
- `gsutil -m rsync -r website/markets.thecloudarchitect.io gs://markets.thecloudarchitect.io/`
