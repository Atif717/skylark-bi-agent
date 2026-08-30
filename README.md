# 🦅 Skylark Monday.com Business Intelligence Agent

An autonomous, conversational Business Intelligence (BI) agent built to dynamically ingest, clean, normalize, join, and analyze messy operational data across Monday.com **Deals** (Sales Pipeline) and **Work Orders** (Project Execution) boards.

---

## 📌 Executive Overview

Business data in fast-growing operational environments is inherently fragmented, noisy, and unstandardized. Founders and executives routinely face challenges when reconciling top-of-funnel sales pipelines with field project execution and revenue realization.

This project delivers an enterprise-grade, conversational BI agent that connects directly to Monday.com boards via dynamic API v2 GraphQL endpoints. It sanitizes real-world data anomalies (such as inconsistent timestamps, mixed currency notations, and duplicated headers), performs multi-board relational joins, and delivers founder-level strategic insights with automated data quality audit caveats.

---

## 🏗️ System Architecture

The application follows a modular, decoupled architecture separating raw board ingestion, resilient data cleansing, tool-based agent orchestration, and an interactive presentation interface:

```
                                  ┌──────────────────────────────┐
                                  │     Monday.com API v2        │
                                  │  (Deals & Work Orders Boards)│
                                  └──────────────┬───────────────┘
                                                 │ GraphQL / Cursor Pagination
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                Data Processing Layer                                    │
│  ┌───────────────────────┐  ┌──────────────────────────┐  ┌─────────────────────────┐   │
│  │     Schema Mapper     │  │   Normalizer & Cleaner   │  │   Data Quality Engine   │   │
│  │ (Internal IDs → Keys) │  │(Dates, Currencies, Text) │  │  (Missingness Auditing) │   │
│  └───────────────────────┘  └──────────────────────────┘  └─────────────────────────┘   │
└───────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                 │ Clean DataFrames + Data Quality Reports
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              Agent & Orchestration Layer                                │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                            Intent Router & LLM Client                             │  │
│  │                   (OpenAI GPT-4o / Groq Llama 3.3 70B Versatile)                  │  │
│  └───────────┬──────────────────────────────┬─────────────────────────────┬──────────┘  │
│              ▼                              ▼                             ▼             │
│  ┌───────────────────────┐    ┌───────────────────────────┐ ┌───────────────────────┐   │
│  │     filter_deals      │    │    filter_work_orders     │ │ join_deals_and_orders │   │
│  ├───────────────────────┤    ├───────────────────────────┤ ├───────────────────────┤   │
│  │       aggregate       │    │generate_leadership_summary│ │ask_clarifying_question│   │
│  └───────────────────────┘    └───────────────────────────┘ └───────────────────────┘   │
└────────────────────────────────────────────────┬────────────────────────────────────────┘
                                                 │ Synthesized Insights + Tables
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          User Interface (Streamlit Cloud)                               │
│         💬 Chat Assistant   │   📊 Data Previews   │   🛡️ Diagnostics & Quality          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Enterprise-Grade Capabilities & Core Features

### 🚀 Zero-Lag Dynamic Monday.com Integration
- Built natively on Monday.com API v2 utilizing cursor-based GraphQL pagination (`items_page { cursor, items }`) and automated exponential-backoff retries.
- Strictly dynamic and read-only — eliminates stale CSV dependencies and ensures live operational accuracy directly from cloud workspaces.

### 🛡️ Production-Ready "Messy Data" Normalization Engine
- **Temporal Parsing:** Ingests and standardizes verbose JavaScript UTC timestamps (`Thu Feb 26 2026... GMT+0000`), ISO strings, and raw Excel epoch leaks into unified `datetime64` dimensions.
- **Financial Cleansing:** Coerces heterogeneous currency expressions (`$`, `Rs.`, `INR`, comma separators, trailing whitespace) into high-precision numeric floats without precision loss.
- **Taxonomy & Header Sanitization:** Cleans repeated spreadsheet header rows leaking across boards and resolves fragmented sector aliases (e.g., auto-standardizing "powerlines" → "Powerline").

### 🔍 Transparent Data Quality & Audit Diagnostics
- Unlike standard LLM wrappers that hallucinate over missing values, our embedded Diagnostic Engine audits missingness across all board dimensions in real time.
- Proactively flags exact data completion percentages (e.g., "⚠️ 92.4% of Close Date values were missing/unparseable") to ensure founders make decisions with calibrated confidence.

### 🔗 Multi-Board Relational Intelligence
- Seamlessly resolves the operational disconnect between top-of-funnel Sales Pipeline (Deals) and bottom-of-funnel Project Execution (Work Orders).
- Executes case-insensitive relational joins on normalized entity identifiers to surface deal progress, unlinked projects, and execution bottlenecks.

### 👑 One-Click Executive Leadership Briefing
- Instantly transforms fragmented board rows into an executive-ready operational brief.
- Unifies total pipeline valuation by sector, operational completion percentages, and cash realization (Billed excl. GST vs. Realized incl. GST) into high-level business intelligence.

### 🧠 Intent Disambiguation & Self-Healing Routing
- Multi-turn conversational intelligence that clarifies ambiguous business requests (e.g., distinguishing fiscal vs. calendar quarters, or billed vs. collected revenue).
- Features a deterministic, fault-tolerant fallback router that ensures 100% response uptime even under transient provider rate limits.

### ⚡ Optimized Low-Latency Streamlit Dashboard
- Engineered with intelligent in-session caching (TTL + manual invalidation triggers), a pinned bottom conversational input, smooth viewport autoscrolling, and dedicated raw data/diagnostic inspection tabs.

---

## 🛠️ Approach & Technical Pipeline

1. **Dynamic Data Fetching** — Queries Monday.com API v2 utilizing cursor-based pagination (`items_page { cursor, items }`), strictly avoiding static CSV file dependencies.
2. **Deterministic Schema Mapping** — Translates auto-generated Monday column hash IDs into standardized semantic keys (`deal_value`, `sector`, `close_date`, `amount_excl_gst`).
3. **Resilient Data Cleaning** — Coerces non-standard date representations and mixed currency strings into clean `datetime64` and numeric float representations without dropping incomplete rows.
4. **Transparent Quality Diagnostics** — Pre-computes column completion rates across boards, enabling the agent to accompany analytical answers with transparency caveats.
5. **Constrained Function Calling** — Leverages an LLM planner that selects specialized analytical tools (`filter_deals`, `filter_work_orders`, `join_deals_and_orders`, `aggregate`, `generate_leadership_summary`), eliminating hallucination risks by executing computations directly in Pandas.

---

## 🤖 AI Tools & Models Used

| Provider | Model | Role |
|---|---|---|
| Groq Cloud | `llama-3.3-70b-versatile` & `llama-3.1-8b-instant` | Primary high-speed inference engine providing sub-second tool planning and narrative generation |
| OpenAI | `gpt-4o` | Supported alternative provider for complex multi-turn semantic reasoning |
| Anthropic | `claude-3-5-sonnet` | Compatible backup provider integrated into the unified `LLMClient` wrapper |
| Deterministic Fallback Engine | — | Rule-based semantic router embedded within `LLMClient` and `AgentOrchestrator` to ensure 100% agent uptime during external API rate-limit spikes or network drops |

---

## 📋 Key Assumptions

- **Entity Linking Key:** In the raw dataset, deal names on the Deals board (e.g., Naruto, Sakura, Goku) map to the primary name column in the Work Orders board, while `deal_name` in Work Orders represents internal Monday IDs (`SDPLDEAL-xxx`). Cross-board relational joins are performed on normalized lowercase name fields.
- **Quarterly Date Conventions:** Queries referencing "quarters" default to standard Calendar Quarters (Q1: Jan–Mar, Q2: Apr–Jun, Q3: Jul–Sep, Q4: Oct–Dec) applied against `close_date` or `tentative_close_date` unless fiscal context is requested.
- **Revenue Realization:** Distinguishes between Pipeline Valuation (prospective sales), Billed Revenue (invoiced amounts excluding GST), and Collected Revenue (cash realized including GST).
- **Non-Destructive Coercion:** Unparseable or missing date and numeric values are coerced to `NaT` or `0.0` rather than dropping the record, preserving overall dataset volume while flagging quality caveats.

---

## ⚖️ Architectural Trade-Offs

| Decision | Alternative Considered | Chosen Approach & Justification |
|---|---|---|
| Data Ingestion | Local CSV files or static database | **Direct GraphQL API v2** — satisfies the strict dynamic ingestion requirement and ensures real-time operational synchronization |
| Agent Execution | Arbitrary Python code interpreter | **Deterministic tool calling** — prevents prompt injection vulnerabilities, enforces schema boundaries, and eliminates LLM arithmetic hallucination |
| Caching Strategy | External Redis / SQL database | **In-memory session caching with TTL & UI refresh** — minimizes infrastructure overhead, reduces Monday.com rate-limit consumption, and provides sub-second query responses |
| Missing Data Policy | Strict row dropping (`dropna`) | **Coercion + audit caveats** — prevents artificial deflation of pipeline value while informing executives of exact missingness percentages |

---

## 👑 Leadership Updates Implementation

The agent includes a dedicated executive briefing tool (`generate_leadership_summary`) accessible via chat or the sidebar quick-action button:

- **Sales Pipeline Health** — Calculates total active pipeline valuation and identifies top-contributing sectors (e.g., Powerline, Mining, Renewables).
- **Operational Execution** — Evaluates the overall project completion percentage across active work orders and highlights pending deliveries.
- **Cash Flow & Realization** — Compares total invoiced revenue (excluding GST) against actual cash collections (including GST) to surface unbilled amounts and outstanding receivables.
- **Data Quality Caveats** — Appends an executive caveat notice detailing missing close dates or unlinked execution items to ensure decisions are made with calibrated confidence.

---

## 🚧 Challenges Faced & Solutions

**Messy Timestamp Variations**
- *Challenge:* Raw date columns mixed verbose JavaScript UTC strings (`Thu Feb 26 2026 18:30:00 GMT+0000`), standard ISO strings, and leaked column headers.
- *Solution:* Implemented a multi-pattern regex date parser (`parse_date_flexible`) in `normalizer.py` that normalizes valid strings and gracefully coerces unparseable values to `NaT`.

**Cross-Board Metric Ambiguity**
- *Challenge:* Grouping columns like `sector` exist in both boards, but financial metrics like `amount_excl_gst` exist only in Work Orders, causing incorrect board selection during generic aggregation queries.
- *Solution:* Upgraded `agent/orchestrator.py` to inspect metric column provenance first before selecting the target DataFrame.

**Provider Rate Limits & Model Deprecation**
- *Challenge:* LLM providers occasionally encounter HTTP 429 quota exhaustion or decommission older model IDs.
- *Solution:* Built an automated model fallback chain in `agent/llm_client.py` (`llama-3.3-70b-versatile` → `llama-3.1-8b-instant`) combined with a deterministic fallback planner to ensure uninterrupted service.

---

## 🚀 Local Setup & Installation

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Git
- Monday.com Developer API Token
- Groq API Key or OpenAI API Key

### 2. Clone the Repository
```bash
git clone https://github.com/Atif717/skylark-bi-agent.git
cd skylark-bi-agent
```

### 3. Set Up Virtual Environment & Dependencies
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
MONDAY_API_TOKEN=your_monday_personal_token
DEALS_BOARD_ID=5030967387
WORK_ORDERS_BOARD_ID=5030967210
OPENAI_API_KEY=gsk_your_groq_api_key_or_openai_key
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
```

### 5. Run Automated Tests
```bash
python -m pytest tests/
```

### 6. Launch the Streamlit App
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ☁️ Streamlit Community Cloud Deployment

To deploy to Streamlit Cloud:

1. Push this repository to GitHub.
2. Connect your repository on [share.streamlit.io](https://share.streamlit.io) with main file path `app.py`.
3. Under **App Settings → Secrets**, paste the following TOML block:

```toml
MONDAY_API_TOKEN = "your_monday_personal_token"
DEALS_BOARD_ID = "5030967387"
WORK_ORDERS_BOARD_ID = "5030967210"
OPENAI_API_KEY = "your_api_key"
LLM_PROVIDER = "groq"
LLM_MODEL = "llama-3.3-70b-versatile"
```

---

## 🔮 Potential Future Improvements

- **Event-Driven Webhook Invalidation** — Replace polling/TTL caching with Monday.com webhooks to invalidate and refresh cache partitions only when specific board items change.
- **Fuzzy & Embedding-Based Entity Resolution** — Implement vector embeddings or Levenshtein distance matching to link client accounts and project names with slight spelling deviations across boards.
- **Automated Data Visualizations** — Integrate Plotly to render interactive pipeline funnel charts, sectoral donut graphs, and cash realization bar charts directly within chat messages.
- **Scheduled Leadership Dispatch** — Implement automated Slack and email dispatches to deliver weekly leadership briefings on a scheduled cadence.
