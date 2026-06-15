---
name: 500-fix-article-quality
description: >-
  Check and improve article quality for financial markets and tech domains.
  Runs domain-specific quality checks (currency, numerical accuracy, compliance,
  SDK symbol verification, sync/async correctness), applies corrections, and
  updates articles via the CMS API. Use when the user says
  "/fix-markets-article-quality", "/fix-article-quality", or mentions article
  quality, editorial review, pipeline metadata findings, or fixing article
  content for markets or tech articles.
---

# Fix Article Quality

Combined skill for checking and improving CMS article quality across two domains: **markets** (financial) and **tech**.

## Quick Start

1. Determine the domain (markets or tech) from the user's command or context.
2. Fetch the article by slug from the CMS API.
3. Read `pipeline_metadata` quality signals.
4. Run domain-specific quality checks.
5. Apply minimal, targeted corrections.
6. Update the article via the API.
7. Report what was fixed, skipped, and flagged.

## Slash Commands

| Command | Domain |
|---------|--------|
| `/fix-markets-article-quality <slug>` | Markets (financial) |
| `/fix-article-quality <slug>` | Tech |

If no slug is provided, ask the user for one.

## Domain Detection

- **Markets**: user mentions markets, financial, currency, tickers, compliance, disclaimer, "not available" density, or uses `/fix-markets-article-quality`.
- **Tech**: user mentions tech article, SDK symbols, technical review, sync/async, code corrections, or uses `/fix-article-quality`.
- If ambiguous, ask the user.

## API Configuration

- **Base URL:** `http://localhost:8001` (Docker backend). Override with env `BACKEND_API_URL`.
- **Markets endpoint:** `GET/PUT /api/v1/domain-articles/markets/{slug}`
- **Tech endpoint:** `GET/PUT /api/v1/domain-articles/tech/{slug}`

Strip any leading slash from the slug before calling.

---

## Shared Workflow

### Step 1 — Fetch Article

```
GET /api/v1/domain-articles/{domain}/{slug}
```

Extract from the response:
- `article.content` — markdown body to correct
- `article.pipeline_metadata` — quality signals
- (Markets only) `article.technical_chart_data`, `article.seo_data`, `article.excerpt`

If 404, report and stop.

### Step 2 — Run Domain-Specific Checks

**Markets domain** → follow [markets-workflow.md](markets-workflow.md)
**Tech domain** → follow [tech-workflow.md](tech-workflow.md)

### Step 3 — Apply Corrections

- Apply only the corrections identified in Step 2.
- Do **not** rewrite narrative beyond what is needed.
- Prefer minimal, targeted changes.
- If a correction is ambiguous, leave it for human review.

### Step 4 — Update Article

```
PUT /api/v1/domain-articles/{domain}/{slug}
Body: {"content": "<corrected markdown>", ...}
```

Include `excerpt` if it was changed (markets). If the update fails (4xx/5xx), report the error and leave the article unchanged.

If no actionable findings remained, do **not** call PUT.

### Step 5 — Report

Summarize in three buckets:
- **Fixed**: what was corrected (with before/after where helpful).
- **Flagged for human review**: items that need manual attention.
- **Passed**: checks that found no issues.

---

## Error Handling

| Condition | Action |
|-----------|--------|
| Article not found (404) | Report and stop |
| `pipeline_metadata` or review missing | Report and stop (tech); proceed with content checks (markets) |
| MCP tool unavailable | Skip that check, note in report |
| API update fails | Leave article unchanged, report error |
| Ambiguous correction | Prefer minimal change, flag for human review |

## Domain-Specific References

- For full markets quality checks, see [markets-workflow.md](markets-workflow.md)
- For full tech quality checks, see [tech-workflow.md](tech-workflow.md)
