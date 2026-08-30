# Engineering & Architectural Decision Log: Skylark BI Agent

---

## 1. Key Assumptions

* **Entity Relationship & Board Linking**: 
  * In the exported Monday.com schema, deal identifiers on the Deals board (e.g., character code names such as `Naruto`, `Sakura`, `Goku`) directly match the primary entity `name` column on the Work Orders board, while `deal_name` in Work Orders corresponds to internal Monday project IDs (`SDPLDEAL-xxx`).
  * Cross-board relational joins are performed using normalized, lowercase `name` strings as the shared primary foreign key.
* **Temporal Disambiguation & Quarter Standards**:
  * Date fields contain heterogeneous formats (verbose JavaScript UTC strings such as `Thu Feb 26 2026 18:30:00 GMT+0000`, standard ISO strings, and raw Excel leaks). These are parsed to standard `datetime64` timestamps.
  * Inquiries regarding "quarters" default to standard Calendar Quarters (Q1: Jan–Mar, Q2: Apr–Jun, Q3: Jul–Sep, Q4: Oct–Dec) applied against `close_date` or `tentative_close_date`.
* **Revenue Metrics Disambiguation**:
  * The system distinguishes between:
    1. *Sales Pipeline Potential* (forecasted deal values from active sales prospects).
    2. *Billed Revenue* (invoiced amounts excluding GST, captured from `amount_excl_gst` / `billed_excl_gst`).
    3. *Collected / Realized Revenue* (cash collections including GST, captured from `collected_incl_gst`).
* **Messy Data Resilience & Missingness Handling**:
  * Missing, corrupt, or unparseable values are coerced to `NaN`/`0.0` rather than dropping the record. 
  * Every aggregation or filtered view is accompanied by an automated Data Quality Caveat tallying the exact percentage of missing values (e.g., `92.4% of Close Date were missing/unparseable`).
* **Header Leak Sanitization**:
  * Duplicate CSV/Excel header rows embedded within board data (e.g., `"Deal Name"`, `"Close Date (A)"`, `"Sector/service"`) are sanitized during ingestion.

---

## 2. Technical Architecture & Trade-Offs Chosen

* **Direct Monday.com GraphQL API v2 with Cursor Pagination vs. MCP / Static CSVs**:
  * *Choice*: Implemented direct GraphQL API v2 queries with cursor pagination (`items_page { cursor, items }`) and retry handling.
  * *Reason*: Satisfies the strict requirement for read-only dynamic data ingestion without hardcoding CSVs, eliminating container orchestration overhead while supporting multi-page fetching.
* **Deterministic Agent Tool Routing vs. Free-form Code Execution**:
  * *Choice*: Constrained JSON tool calling (`filter_deals`, `filter_work_orders`, `join_deals_and_orders`, `aggregate`, `generate_leadership_summary`).
  * *Reason*: Eliminates prompt injection and arbitrary code execution vulnerabilities, prevents LLM arithmetic hallucination by delegating math to Pandas, and ensures deterministic outputs.
* **Resilient Multi-Provider LLM Client with Fallback Chains**:
  * *Choice*: Multi-provider client supporting OpenAI, Groq, and Anthropic with automatic model failover (`llama-3.3-70b-versatile` $\rightarrow$ `llama-3.1-8b-instant`) and a heuristic fallback router.
  * *Reason*: Prevents application crashes during transient API outages, quota exhaustion (HTTP 429), or model deprecation errors.
* **In-Memory Session Caching vs. Persistent Database**:
  * *Choice*: Session-level in-memory cache with TTL and an on-demand UI refresh trigger (`Refresh data from monday.com`).
  * *Reason*: Avoids external database infrastructure, reduces API rate-limit consumption on Monday.com, and delivers sub-second response times for executive queries.

---

## 3. Interpretation & Implementation of "Leadership Updates"

The Leadership BI Summary is designed as an executive briefing that unites top-of-funnel pipeline health with bottom-of-funnel operational execution and cash realization:

1. **Pipeline & Valuation Health**:
   * Aggregates total contract potential across active deal stages (Prospect, Won, Open).
   * Identifies top-contributing sectors (e.g., Powerline, Mining, Renewables) with valuation breakdowns.
2. **Operational Project Execution**:
   * Measures the overall Work Order Completion Rate (percentage of projects completed vs. in-flight/stuck).
   * Highlights ongoing project counts and delivery queues.
3. **Financial Realization & Cash Collection**:
   * Compares total billed revenue (excl. GST) against actual realized collections (incl. GST).
   * Computes outstanding receivables to provide leadership with immediate cash flow visibility.
4. **Transparent Data Auditing**:
   * Appends an executive caveat notice detailing data gaps (e.g., unlinked work orders or unrecorded close dates).

---

## 4. What I'd Do Differently With More Time

* **Event-Driven Webhooks**:
  * Replace polling/TTL caching with Monday.com webhook endpoints to invalidate and update cache partitions only when specific board items change.
* **Vector Embeddings & Fuzzy Entity Resolution**:
  * Integrate embedding-based vector similarity (or Levenshtein distance) to join entity names and client accounts with slight spelling deviations across boards.
* **Automated Data Visualizations**:
  * Integrate Plotly to render interactive pipeline funnel charts, sectoral donut graphs, and cash realization bar charts alongside markdown tables.
* **Role-Based Access & Scheduled Dispatch**:
  * Add user authentication and automated Slack/Email weekly dispatch for Monday morning leadership briefs.
