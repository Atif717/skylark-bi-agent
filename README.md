# Skylark BI Agent

Skylark BI Agent is a Streamlit-based business intelligence assistant that interfaces with Monday.com boards (Deals and Work Orders) using a thin GraphQL client. It normalizes retrieved data, performs data quality checks, and leverages LLMs (OpenAI or Anthropic) to orchestrate and answer user questions in plain English through tools (querying, joining, and aggregating datasets).

## Project Architecture

```
skylark-bi-agent/
├── .env                          # Monday.com API token, board IDs (never commit)
├── .env.example                  # Template for README instructions
├── .gitignore
├── requirements.txt
├── README.md                     # Architecture + setup instructions
├── decision_log.md               # Deliverable detailing architectural choices
│
├── app.py                        # Streamlit entrypoint (chat UI)
│
├── config/
│   └── settings.py               # Loads .env, exposes BOARD_IDS, API_TOKEN, MODEL config
│
├── monday_client/
│   ├── __init__.py
│   ├── client.py                 # Thin GraphQL client (auth headers, execute_query)
│   ├── queries.py                # GraphQL query strings/templates (items_page, columns, etc.)
│   └── fetch.py                  # High-level functions: get_deals(), get_work_orders()
│
├── data_processing/
│   ├── __init__.py
│   ├── normalizer.py             # Date parsing, text/naming cleanup, null handling
│   ├── schema.py                 # Column-name mapping (Monday column IDs -> friendly names)
│   └── quality.py                # Data quality flags (missing %, inconsistent formats found)
│
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py           # Main "answer this query" logic — routes to tools
│   ├── tools.py                  # Callable functions the LLM can invoke
│   ├── prompts.py                # System prompt(s), clarifying-question logic
│   └── llm_client.py             # Wrapper around Anthropic/OpenAI API call
│
├── cache/
│   └── .gitkeep                  # Cache directory marker
│
└── tests/
    ├── test_normalizer.py
    ├── test_monday_client.py
    └── test_agent_tools.py
```

## Setup Instructions

### Prerequisites
- Python 3.10+
- A Monday.com API Token and access to target Deals and Work Orders boards.

### Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd skylark-bi-agent
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables by copying `.env.example` to `.env` and updating the values:
   ```bash
   cp .env.example .env
   ```

### Running the Application

1. Start the Streamlit application:
   ```bash
   streamlit run app.py
   ```

2. Open the URL printed in the terminal (usually `http://localhost:8501`) to interact with the chat interface.

### Running Tests

Execute tests using `pytest`:
```bash
pytest tests/
```
