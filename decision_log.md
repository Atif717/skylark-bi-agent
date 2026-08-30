# Skylark BI Agent — Decision Log

## 1. Key Assumptions
* **Entity Relationship & Board Joins**: In the messy Monday.com export, deal titles on the Deals board (e.g., character code names like `Naruto`, `Sakura`, `Goku`) map directly to the primary entity `name` column in the Work Orders board, whereas `deal_name` in Work Orders corresponds to internal Monday project IDs (`SDPLDEAL-xxx`). Cross-board joins use `name` as the primary joining key.
* **Temporal Logic & Quarter Conventions**:
  * Date fields often contain verbose UTC timestamps (`Thu Feb 26 2026 ... GMT+0000`) or header leaks. These are cleaned and parsed to standard `datetime64`.
  * Calendar quarters (Q1: Jan–Mar, Q2: Apr–Jun, Q3: Jul–Sep, Q4: Oct–Dec) are applied to `close_date` and `tentative_close_date`.
* **Ambiguity Handling**: When founder queries lack necessary boundaries (e.g., unspecified fiscal vs calendar quarters or ambiguous sector spellings), the agent prompts clarifying questions rather than silently hallucinating assumptions.
* **Header Leak Handling**: Repeated Excel header rows embedded within board data (e.g., `"Deal Name"`, `"Close Date (A)"`, `"Sector/service"`) are sanitized during ingestion.

---

## 2. Trade-Offs Chosen & Justifications
* **In-Memory Session Caching vs. Persistent Database**:
  * *Choice*: Session-level in-memory cache with manual on-demand refresh via the UI.
  * *Reason*: For an ad-hoc executive BI assistant, this eliminates database setup overhead, minimizes API rate-limit consumption on Monday.com, and ensures immediate responsiveness without complex caching infrastructure.
* **Deterministic Function Calling vs. Free-form Python Code Interpreter**:
  * *Choice*: Constrained tool calling (`filter_deals`, `filter_work_orders`, `join_deals_and_orders`, `aggregate`, `generate_leadership_summary`).
  * *Reason*: Guarantees mathematical accuracy, prevents prompt injection/code execution security risks, and enforces strict schema compliance.
* **Data Resilience with Explicit Caveats**:
  * *Choice*: Non-blocking coercion where corrupted values fallback to `NaN`/`0.0`, accompanied by an explicit data quality caveat banner.
  * *Reason*: Founders receive actionable answers immediately while being informed of the exact margin of missing or unparseable records (e.g., `92.4% of Close Date were missing`).

---

## 3. Interpretation of "Leadership Updates"
The Leadership BI Summary is designed as an executive briefing synthesized across three pillars:
1. **Pipeline & Valuation Health**: Total contract potential, active prospect count, and sector-wise distribution (e.g., Powerline vs Mining vs Renewables).
2. **Operational Project Execution**: Total work orders, completion rate percentage, and ongoing delivery status.
3. **Financial Realization & Cash Flow**: Aggregate revenue billed (excl. GST) vs actual collected revenue (incl. GST), highlighting unbilled or pending receivables.

---

## 4. What I'd Do Differently With More Time
* **Live Webhook Integration**: Implement Monday.com webhooks to invalidate and refresh cache only when board items are updated, created, or deleted.
* **Semantic & Fuzzy Entity Matching**: Integrate vector embeddings or Levenshtein distance matching to link client names and company entities with slight spelling deviations across boards.
* **Interactive Visualization Engine**: Auto-generate dynamic Plotly charts (e.g., pipeline funnels, sectoral breakdown donuts) alongside tabular outputs.