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

## ✨ Core Features

* **Dynamic Monday.com Integration**: Reads data directly from Monday.com API v2 with GraphQL cursor pagination and transient error retries (no hardcoded CSVs).
* **Messy Data Resilience**: 
  * Normalizes inconsistent date representations (e.g., verbose UTC JavaScript timestamps, ISO strings, Excel leaks).
  * Cleans currency strings with mixed notations (`$`, `Rs.`, `INR`, commas).
  * Standardizes naming variants and sector aliases (e.g., `powerlines` $\rightarrow$ `Powerline`).
  * Sanitizes duplicate Excel header leaks embedded across boards.
* **Transparent Data Quality Engine**: Tallies and communicates missing/unparseable value percentages per column directly to the user (e.g., *"92.4% of Close Date were missing"*).
* **Multi-Board Relational Intelligence**: Cross-joins sales prospects with ongoing execution work orders on common entity identifiers.
* **Executive Leadership BI Summary**: Synthesizes pipeline health, operational delivery rates, and cash collection metrics into an executive-ready brief.
* **Interactive Chat UI**: Built with Streamlit, including session history, in-memory caching with manual refresh, and data quality preview tabs.

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