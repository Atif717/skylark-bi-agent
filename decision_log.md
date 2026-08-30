# Skylark BI Agent - Architectural Decision Log

This document records the design choices and architectural decisions for the Skylark BI Agent.

## 1. Directory Structure and Module Boundaries

We opted for a modular directory structure that clearly separates the application interface, external API calls, data cleaning and quality validation, and the LLM agent orchestration logic:

*   **`config/`**: Centralized configuration management. Isolates environment variable reading and prevents raw `os.environ` usage throughout the app.
*   **`monday_client/`**: Encapsulates all interactions with Monday.com's API. Employs a thin GraphQL client instead of heavy third-party libraries for maximal control over request structures.
*   **`data_processing/`**: Isolates schema definitions, type normalization, and quality validation. This ensures the downstream LLM tools operate on clean, typed, and schema-consistent dataframes.
*   **`agent/`**: The core LLM orchestrator. Contains LLM clients, agent prompt templates, tool descriptions, and the execution loop.
*   **`tests/`**: Unit test suite to verify client responses, schema mapping, normalizer logic, and tool execution.

## 2. API Integration: Thin GraphQL Client vs. SDK

**Decision**: Build a thin, native HTTP client using `requests` to execute GraphQL queries.
*   **Rationale**:
    *   Third-party Python SDKs for Monday.com often lag behind new API versions (Monday API version `2024-01` and later).
    *   Monday.com is fundamentally a GraphQL API. Writing raw GraphQL query strings allows us to request precisely the column values we need, reducing payload size and increasing speed.
    *   Error handling for rate limits (HTTP 429) and GraphQL errors (HTTP 200 containing an `errors` key) is more reliable when handled directly at the network layer.

## 3. Data Processing and Cleaning Pipeline

**Decision**: Multi-stage pipeline: Schema mapping -> Column normalization -> Quality reporting.
*   **Schema Mapping (`schema.py`)**: Maps Monday's physical column IDs (e.g. `date_1`, `numeric_3`) to developer-friendly semantic labels (e.g. `close_date`, `deal_size`).
*   **Column Normalization (`normalizer.py`)**:
    *   Parses inconsistent date representations into standardized ISO datetimes or clean Pandas date columns.
    *   Converts values from currency/text representations into pure numeric formats.
    *   Fills or highlights null values explicitly to avoid runtime Pandas computation errors.
*   **Quality Reporting (`quality.py`)**: Generates simple stats (null percentage, format consistency) that are fed to the LLM agent context to prevent hallucinations on incomplete data.

## 4. LLM Orchestration Strategy: ReAct vs. Function Calling

**Decision**: Structured tool invocation using function calling schema or explicit prompt routing, wrapped in a simple linear Orchestrator.
*   **Rationale**:
    *   Streamlit requires fast, predictable responses. A loose ReAct loop can loop indefinitely or make erratic tool calls.
    *   By packaging operations as deterministic tools (e.g., `query_deals()`, `join_boards()`, `aggregate_metrics()`), the LLM focuses on parameter binding and logic interpretation rather than writing raw code.
    *   The wrapper in `llm_client.py` supports both Anthropic's Claude and OpenAI's GPT models via a single interface, offering vendor independence.

## 5. Local Cache Strategy

**Decision**: File-based local cache (`cache/`) with timestamp validation.
*   **Rationale**:
    *   Monday.com API rate limits can easily be hit under frequent chat queries.
    *   Data fetched is stored as local serialized JSON or Parquet with a configured TTL (Time To Live). If a query happens within the TTL, cache data is served instantly, ensuring a snappy Streamlit experience.
