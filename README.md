# Skylark Monday.com Business Intelligence Agent

An AI-driven conversational Business Intelligence (BI) agent built to dynamically ingest, clean, join, and analyze messy operational data across **Monday.com Deals** (Sales Pipeline) and **Work Orders** (Project Execution) boards.

---

## 🏗️ System Architecture

```
                                  ┌───────────────────────────┐
                                  │      Monday.com API       │
                                  │ (Deals & Work Orders)     │
                                  └─────────────┬─────────────┘
                                                │ GraphQL / Cursor Pagination
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                Data Processing Layer                                   │
│  ┌───────────────────────┐  ┌──────────────────────────┐  ┌─────────────────────────┐  │
│  │     Schema Mapper     │  │  Normalizer & Cleaner    │  │   Data Quality Engine   │  │
│  │ (Internal IDs ➔ Keys) │  │  (Dates, Currency, Text) │  │   (Missing Data Tally)  │  │
│  └───────────────────────┘  └──────────────────────────┘  └─────────────────────────┘  │
└───────────────────────────────────────────────┬────────────────────────────────────────┘
                                                │ Clean DataFrames + Quality Caveats
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  Agent & Tool Layer                                    │
│  ┌────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │   filter_deals     │  │   filter_work_orders    │  │   join_deals_and_orders     │  │
│  ├────────────────────┤  ├─────────────────────────┤  ├─────────────────────────────┤  │
│  │   aggregate        │  │  leadership_summary     │  │   Ambiguity Clarifier       │  │
│  └────────────────────┘  └─────────────────────────┘  └─────────────────────────────┘  │
└───────────────────────────────────────────────┬────────────────────────────────────────┘
                                                │ Function Calling Loop
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         User Interface (Streamlit Cloud)                               │
│            Chat Assistant  │  Data Quality Diagnostics  │  Leadership Actions          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Enterprise-Grade Capabilities & Core Features

* 🚀 **Zero-Lag Dynamic Monday.com Integration**
  * Built natively on Monday.com API v2 utilizing cursor-based GraphQL pagination (`items_page { cursor, items }`) and automated exponential-backoff retries[cite: 3].
  * Strictly dynamic and read-only—eliminates stale CSV dependencies and ensures live operational accuracy directly from cloud workspaces[cite: 3].

* 🛡️ **Production-Ready "Messy Data" Normalization Engine**
  * **Temporal Parsing**: Ingests and standardizes verbose JavaScript UTC timestamps (`Thu Feb 26 2026... GMT+0000`), ISO strings, and raw Excel epoch leaks into unified `datetime64` dimensions.
  * **Financial Cleansing**: Coerces heterogeneous currency expressions (`$`, `Rs.`, `INR`, comma separators, trailing whitespace) into high-precision numeric floats without precision loss.
  * **Taxonomy & Header Sanitization**: Cleans repeated spreadsheet header rows leaking across boards and resolves fragmented sector aliases (e.g., auto-standardizing `powerlines` $\rightarrow$ `Powerline`).

* 🔍 **Transparent Data Quality & Audit Diagnostics**
  * Unlike standard LLM wrappers that hallucinate over missing values, our embedded Diagnostic Engine audits missingness across all board dimensions in real time[cite: 3].
  * Proactively flags exact data completion percentages (e.g., *"⚠️ 92.4% of Close Date values were missing/unparseable"*) to ensure founders make decisions with calibrated confidence[cite: 3].

* 🔗 **Multi-Board Relational Intelligence**
  * Seamlessly resolves the operational disconnect between top-of-funnel Sales Pipeline (Deals) and bottom-of-funnel Project Execution (Work Orders)[cite: 3].
  * Executes case-insensitive relational joins on normalized entity identifiers to surface deal progress, unlinked projects, and execution bottlenecks[cite: 3].

* 👑 **One-Click Executive Leadership Briefing**
  * Instantly transforms fragmented board rows into an executive-ready operational brief[cite: 3].
  * Unifies total pipeline valuation by sector, operational completion percentages, and cash realization (Billed Excl. GST vs. Realized Incl. GST) into high-level business intelligence[cite: 3].

* 🧠 **Intent Disambiguation & Self-Healing Routing**
  * Multi-turn conversational intelligence that clarifies ambiguous business requests (e.g., distinguishing fiscal vs. calendar quarters, or billed vs. collected revenue)[cite: 3].
  * Features a deterministic, fault-tolerant fallback router that ensures 100% response uptime even under transient provider rate limits[cite: 3].

* ⚡ **Optimized Low-Latency Streamlit Dashboard**
  * Engineered with intelligent in-session caching (TTL + manual invalidation triggers), a pinned bottom conversational input, smooth viewport autoscrolling, and dedicated raw data/diagnostic inspection tabs[cite: 3].
---

## 🚀 Local Setup & Installation

### Prerequisites
* **Python 3.10+** (Python 3.11 recommended)
* **Git**
* A **Monday.com API Token**
* An **OpenAI API Key** (or compatible LLM provider key)

### 1. Clone the Repository
```bash
git clone [https://github.com/Atif717/skylark-bi-agent.git](https://github.com/Atif717/skylark-bi-agent.git)
cd skylark-bi-agent
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
MONDAY_API_TOKEN=your_monday_personal_token
DEALS_BOARD_ID=5030967387
WORK_ORDERS_BOARD_ID=5030967210
OPENAI_API_KEY=your_openai_api_key
LLM_PROVIDER=openai
```

### 5. Run the Automated Tests
```bash
python -m pytest tests/
```

### 6. Launch the Streamlit Application
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## ⚙️ Connecting Your Own Monday.com Boards

To plug in custom Monday.com boards:

1. Obtain your API token from **Monday.com $\rightarrow$ Developer Section $\rightarrow$ API**.
2. Find your **Board IDs** from your board's URL: `https://your-team.monday.com/boards/<BOARD_ID>`.
3. Update `DEALS_BOARD_ID` and `WORK_ORDERS_BOARD_ID` in your `.env` (or Streamlit Cloud Secrets).
4. If your imported column structure generates custom internal IDs, update `DEALS_SCHEMA` and `WORK_ORDERS_SCHEMA` in `data_processing/schema.py` to match the column IDs.

---

## ☁️ Deployment (Streamlit Community Cloud)

1. Fork/push this repository to your GitHub account.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and create a **New app**.
3. Select this repository and set the main entry file to `app.py`.
4. In **Advanced Settings $\rightarrow$ Secrets**, paste the following:
   ```toml
   MONDAY_API_TOKEN = "your_monday_personal_token"
   DEALS_BOARD_ID = "5030967387"
   WORK_ORDERS_BOARD_ID = "5030967210"
   OPENAI_API_KEY = "your_openai_api_key"
   LLM_PROVIDER = "openai"
   ```
5. Click **Deploy**.

---

## 📁 Repository Structure

```
skylark-bi-agent/
├── agent/
│   ├── __init__.py
│   ├── llm_client.py       # LLM provider wrapper
│   ├── orchestrator.py     # Function calling loop & query router
│   ├── prompts.py          # System prompts & ambiguity guidelines
│   └── tools.py            # Business intelligence tools
├── config/
│   └── settings.py         # Environment & credentials loader
├── data_processing/
│   ├── __init__.py
│   ├── normalizer.py       # Date, numeric, and text cleaning
│   ├── quality.py          # Quality audit & caveat tallying
│   └── schema.py           # Monday.com column ID mappings
├── monday_client/
│   ├── __init__.py
│   ├── client.py           # Raw API v2 POST client & retries
│   ├── fetch.py            # Board item extraction & schema flattening
│   └── queries.py          # GraphQL queries with cursor pagination
├── tests/
│   ├── test_agent_tools.py
│   ├── test_monday_client.py
│   └── test_normalizer.py
├── app.py                  # Streamlit chat interface & dashboard
├── decision_log.md         # Key assumptions, trade-offs, and design decisions
├── pytest.ini              # Test runner configuration
├── requirements.txt        # Runtime dependencies
└── README.md
```
