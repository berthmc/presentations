---
name: 400-gemini-auth
description: >-
  Configures Gemini / Vertex AI authentication for the CMS and TA repos. Use when working
  with Gemini, Vertex AI, LLM auth, or debugging ADC issues.
---

# Gemini / Vertex AI Authentication

## Canonical Rule
Use **Vertex AI only** — never rely on a consumer Gemini API key for these projects.

## Local Development (CMS & TA)
1. Place the Vertex AI service account JSON at:
   - CMS: `src/cms/secrets/vertexai_sa.json`
   - TA: `src/technicalanalysis/credentials/vertexai_sa.json`
2. In `.env`, set:
   - `GOOGLE_APPLICATION_CREDENTIALS` pointing to the respective JSON path.
   - `GCP_PROJECT_ID` (optional if `project_id` is inside the JSON).
   - `VERTEX_REGION=europe-west1`

## Cloud Run / Production
- When `GCP_PROJECT_ID` is set and there is no credentials file on disk, the backend uses **Application Default Credentials (ADC)**.
- The Cloud Run service account must have `roles/aiplatform.user`.

## Models
- `google-cloud-aiplatform` or `google-genai` libraries should be instantiated with `vertexai=True`.
- Use `gemini-2.0-flash` for drafts, `gemini-2.5-pro` for reasoning/quality scoring.
