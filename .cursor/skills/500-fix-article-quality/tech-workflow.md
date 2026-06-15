# Tech Article Quality Checks

Detailed quality checks for tech articles. Referenced from [SKILL.md](SKILL.md) Step 2.

## Pipeline Metadata Fields

From `pipeline_metadata.technical_review`, extract:
- `findings` — list of symbol verification results
- `not_found` — symbols that could not be verified
- `outdated_models` — LLM model identifiers flagged as retired/superseded
- `warnings` — sync/async and other warnings

If `technical_review` is missing or `technical_review.skipped` is true, report that no quality report is available and stop.

## Finding Classification

For each finding, classify and decide action:

### Skip (No Action)

| Category | Rule | Examples |
|----------|------|----------|
| Verified | `status == "verified"` | Already confirmed correct |
| Stdlib / builtin | Symbol is a Python stdlib name | `datetime`, `timezone`, `random`, `dumps`, `getenv`, `isoformat`, `now`, `uniform`, `post`, `run`, `predict` |
| Placeholder class | PascalCase name that does not match a known SDK | `WaterQualityPredictor`, `DataProcessor` |

Count stdlib skips as false positives. Note placeholder classes for human review (do not replace).

### Act — SDK Symbol Lookup

**Condition:** `status == "not_found"` AND symbol looks like an SDK class or method (known SDK pattern, or appears in code importing from `azure`, `google`, `boto3`, `openai`).

**Action:** Resolve via Context7 (see below).

### Act — Outdated Model Reference

**Condition:** `status == "outdated_model"` — the finding includes a `replacement` field with the recommended current model.

**Action:** Replace the retired model identifier with the recommended replacement everywhere it appears in code blocks, inline code, and prose. The `note` field contains the suggested replacement.

### Act — Sync/Async Fix

**Condition:** `status == "warning"` AND message indicates sync/async mismatch — article code imports from an async-capable SDK (e.g. `azure.ai.projects`, `google.cloud.*`) without `.aio` but uses `await`.

**Action:** Fix imports to use the `.aio` submodule and keep `await` usage.

## Context7 SDK Symbol Resolution

For each "look up via Context7" symbol:

1. **Resolve library ID:**
   Call `resolve-library-id` on MCP server **`user-context7`** with a query including the symbol or the implied library name (e.g. `azure-ai-projects`, `google-cloud-monitoring`).

2. **Query docs:**
   Call `get-library-docs` with the resolved library ID and a query including the symbol.

3. **Determine correction:**
   From the returned docs, find the correct class name, method name, or import path. Use that for the correction.

4. **If no docs found:**
   Do **not** invent a correction. Leave a note for human verification.

## Applying Corrections

In the markdown `content`:
- **SDK symbols:** replace wrong names with the correct names from Context7. Change only the minimal necessary (class name, method name, or import line).
- **Outdated models:** replace retired model identifiers with the recommended replacement everywhere they appear (code blocks, inline code, prose).
- **Sync/async:** in Python code blocks, change imports from e.g. `from azure.ai.projects import X` to `from azure.ai.projects.aio import X` where `await` is used with that client. Apply similarly for `google`, `boto3`, etc.
- **Do not modify:** stdlib usage, placeholder classes, verified symbols, or prose beyond what corrections require.

## Notes

- Stdlib and builtin names (`datetime`, `json.dumps`, `os.getenv`, etc.) are excluded from the pipeline verifier and should be skipped here as well.
- Placeholder or illustrative class names should not be replaced with real SDK classes unless the article clearly intends to use a specific SDK.
