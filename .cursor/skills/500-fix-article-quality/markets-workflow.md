# Markets Article Quality Checks

Detailed quality checks for financial/markets articles. Referenced from [SKILL.md](SKILL.md) Step 2.

## Pipeline Metadata Fields

From `pipeline_metadata`, read:
- `quality_score`
- `data_quality_warnings`
- `data_verification`
- `editorial_review`
- `research_evidence`

## Quality Checks

### 1. Currency Accuracy

Detect exchange prefix from `technical_chart_data.stocks[].ticker`:
- **EUR-listed:** `ETR:`, `EPA:`, `XETRA:`, `.PA` → use EUR or €
- **USD-listed:** `NYSE:`, `NASDAQ:`, `.US` → use USD or $

Flag any `$` in content when the article covers EUR-listed tickers. Replace with EUR/€ as appropriate.

### 2. Numerical Spot-Check

Compare prices and percentages in the content to `technical_chart_data.stocks` fields:
- `price`, `price_change_pct`, `rsi_14.value`

Flag and correct mismatches between content and stored data.

### 3. Financial MCP Live Price Lookup

For each unique ticker in `technical_chart_data.stocks`:
- Call **`fetch_live_price(ticker)`** on MCP server **`project-0-cms-financial`**.
- Compare live price to article's stated price and to stored `technical_chart_data` values.

Decision logic:
- **Article matches stored data, but both differ from live** (>5%): note for human review only (stale generation-time data, not a content error). Do not change.
- **Article differs from stored data**: content error — correct to match stored pipeline data.
- **MCP unavailable**: skip live comparison, rely on numerical spot-check only. Note in report.

### 4. "Not Available" Density

Count occurrences of: "not available", "no data", "unavailable", "was not available".

If **> 2 occurrences**: condense into a single brief note and remove repetition.

### 5. Vague Filler / Pipeline Jargon

Flag and remove or rephrase:
- "leads me to believe", "appears to be linked"
- "draft data", "my system", "my scans"
- "signal score" used out of context

### 6. Data Completeness per Ticker

From `technical_chart_data.stocks`, flag tickers with all-null TA data (no price, no RSI, no signal). Shorten or merge prose for those tickers instead of writing long "not available" paragraphs.

### 7. Compliance / Disclaimer

Verify a disclaimer paragraph exists, e.g.:
> "This content is for educational and informational purposes only and does not constitute financial advice."

If missing, append a short standard disclaimer at the end.

### 8. Persona / Brand Leak

Check `excerpt` and `content` for hardcoded persona or brand names (e.g. "Mark from Clear Signals"). Remove or replace with neutral wording.

### 9. Citation Relevance (Informational Only)

From `research_evidence.citations`, flag citations whose title clearly does not match the assigned ticker's company (e.g. a gold mining article cited for a Volkswagen ticker).

Report for awareness only — **no content change required**.

## Post-Correction Options

After updating the article content via PUT, optionally refresh the editorial review:

| Method | Endpoint | When |
|--------|----------|------|
| Re-run reviewer (LLM) | `POST /api/v1/markets/articles/{slug}/re-run-editorial-review` | Want stored review to reflect corrected text |
| Patch verdict only | `PUT /api/v1/domain-articles/markets/{slug}` with `pipeline_metadata.editorial_review` | Only need to clear/adjust stored verdict |

## Notes

- Markets articles use `content` (markdown) and optional `excerpt`.
- Exchange prefixes `ETR`, `EPA`, `XETRA`, `.PA` → European (EUR/€). `NYSE`, `NASDAQ`, `.US` → USD ($).
