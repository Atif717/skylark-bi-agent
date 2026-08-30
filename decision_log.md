# Engineering & Architectural Decision Log: Skylark BI Agent

---

## 1. Key Assumptions

* **Entity Relationship & Board Linking**:
  * In the exported Monday.com schema, the Deals board's primary entity `name` column (e.g., character code names such as `Naruto`, `Sakura`, `Goku`) is the human-readable deal name. On the Work Orders board, that same deal name is stored in the **`deal_name`** column (e.g., internal Monday project IDs like `SDPLDEAL-xxx` when present, or the matching character-code name), while Work Orders' own `name` column is a separate identifier for the execution/project record itself.
  * Cross-board relational joins are therefore performed as `deals.name == work_orders.deal_name`, using normalized, lowercase strings as the shared foreign key — **not** `name == name` across both boards, since those two columns represent different entities on each board and never reliably match. This was caught during testing (see §4) and corrected before submission.
* **Temporal Disambiguation & Quarter Standards**:
  * Date fields contain heterogeneous formats (verbose JavaScript UTC strings such as `Thu Feb 26 2026 18:30:00 GMT+0000`, standard ISO strings, and raw Excel leaks). These are parsed to standard `datetime64` timestamps.
  * Inquiries regarding "quarters" default to standard Calendar Quarters (Q1: Jan–Mar, Q2: Apr–Jun, Q3: Jul–Sep, Q4: Oct–Dec) applied against `close_date` or `tentative_close_date`, unless the user specifies "fiscal."
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
* **Conversation Continuity Is Part of "Handling Ambiguity"**:
  * A single user question is often split across multiple turns (agent asks a clarifying question, user answers in a short follow-up like "calendar" or "billed"). The agent is assumed to need the last several turns of chat history, not just the current message, to correctly resolve these follow-ups and to avoid re-asking a question the user already answered.

---

## 2. Technical Architecture & Trade-Offs Chosen

* **Direct Monday.com GraphQL API v2 with Cursor Pagination vs. MCP / Static CSVs**:
  * *Choice*: Implemented direct GraphQL API v2 queries with cursor pagination (`items_page { cursor, items }`) and retry handling.
  * *Reason*: Satisfies the strict requirement for read-only dynamic data ingestion without hardcoding CSVs, eliminating container orchestration overhead while supporting multi-page fetching.
* **Deterministic Agent Tool Routing vs. Free-form Code Execution**:
  * *Choice*: Constrained JSON tool calling (`filter_deals`, `filter_work_orders`, `join_deals_and_orders`, `aggregate`, `generate_leadership_summary`).
  * *Reason*: Eliminates prompt injection and arbitrary code execution vulnerabilities, prevents LLM arithmetic hallucination by delegating math to Pandas, and ensures deterministic outputs.
* **Resilient Multi-Provider LLM Client with Fallback Chains**:
  * *Choice*: Multi-provider client supporting OpenAI, Groq, and Anthropic with automatic model failover (`llama-3.3-70b-versatile` → `llama-3.1-8b-instant`) and a heuristic, keyword-driven fallback router when no provider is reachable at all.
  * *Reason*: Prevents application crashes during transient API outages, quota exhaustion (HTTP 429), or model deprecation errors.
  * *Refinement*: The fallback router was upgraded to extract entities (sector, deal stage, work-order status) against the full canonical vocabulary used by the normalizer, rather than a single hardcoded keyword. It also considers the last few turns of chat history, so a filter mentioned before a clarifying question isn't lost by the time the user answers it.
* **Conversation History Passed to the LLM (and to the Fallback Router)**:
  * *Choice*: The last several chat turns (pulled from session state) are sent alongside every query, to both the real LLM call and the rule-based fallback, rather than treating each message as an isolated, context-free query.
  * *Reason*: Without this, replying "calendar" to the agent's own "calendar or fiscal?" clarifying question loses the original question's filters (e.g. sector) entirely, since the reply alone carries none of that context.
* **Deterministic, Pandas-Based Insight Narratives Instead of a Second LLM Call**:
  * *Choice*: After a tool returns a result table, the natural-language summary shown above it (row counts, totals, top group breakdowns) is computed directly from the DataFrame in Python, not generated by a second round-trip to the LLM.
  * *Reason*: Guarantees the narrative can never contradict the table displayed beneath it, avoids doubling per-query LLM cost/latency, and keeps the feature working even when the LLM provider is completely unreachable.
* **In-Memory Session Caching vs. Persistent Database**:
  * *Choice*: Session-level in-memory cache with TTL and an on-demand UI refresh trigger (`Refresh data from monday.com`).
  * *Reason*: Avoids external database infrastructure, reduces API rate-limit consumption on Monday.com, and delivers sub-second response times for executive queries.
  * *Known limitation*: on Streamlit Community Cloud, this cache currently lives on disk per-process rather than strictly per-user session, so concurrent users on the same instance can observe each other's `force_refresh`/TTL state. Acceptable for a single-tenant demo; flagged in §4 for a real multi-tenant deployment.

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

* **Caught During Testing — Worth Flagging Explicitly**: the original cross-board join implementation matched `work_orders.name` against `deals.name`, which — per the schema above — are two unrelated identifiers (a Work Order's own item name vs. a Deal's name). This meant `join_deals_and_orders` silently returned zero rows for every query, passing without error but never actually joining anything. It was only caught by running the existing unit test suite (`test_join_deals_and_orders`) before final submission and fixed to join on `deals.name == work_orders.deal_name` instead. With more time, I'd add an assertion/log line that fires whenever a join returns an empty result on non-empty inputs, so this class of silent failure surfaces immediately during manual testing rather than depending on a unit test catching it.
* **Event-Driven Webhooks**:
  * Replace polling/TTL caching with Monday.com webhook endpoints to invalidate and update cache partitions only when specific board items change.
* **Vector Embeddings & Fuzzy Entity Resolution**:
  * Integrate embedding-based vector similarity (or Levenshtein distance) to join entity names and client accounts with slight spelling deviations across boards — useful since the current exact-match join is sensitive to typos or truncation in either `name` or `deal_name`.
* **True Multi-Tool Query Planning**:
  * The agent currently resolves each query to a single tool call. A question like "pipeline for energy sector this quarter, cross-referenced with execution status" really needs `filter_deals` + `join_deals_and_orders` chained together. A small planning loop that lets the LLM call more than one tool per turn (or a lightweight ReAct-style loop) would handle these compound questions more naturally instead of forcing them into one tool's parameter set.
* **Automated Data Visualizations**:
  * Integrate Plotly to render interactive pipeline funnel charts, sectoral donut graphs, and cash realization bar charts alongside markdown tables.
* **Per-User Cache Isolation**:
  * Move the on-disk cache to `st.session_state` (or a per-session-scoped store) so concurrent users on shared Streamlit Cloud infrastructure don't share cache/refresh state.
* **Role-Based Access & Scheduled Dispatch**:
  * Add user authentication and automated Slack/Email weekly dispatch for Monday morning leadership briefs.
