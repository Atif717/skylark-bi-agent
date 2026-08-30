import os
import json
import time
import pandas as pd
import logging
from config.settings import settings
from monday_client.client import MondayClient
from monday_client.fetch import get_deals, get_work_orders
from data_processing.normalizer import normalize_deals, normalize_work_orders
from .llm_client import LLMClient
from .prompts import SYSTEM_PROMPT
from . import tools

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
CACHE_TTL = 300  # Cache TTL: 5 minutes

class AgentOrchestrator:
    """
    Main BI Agent Orchestrator class. Manages cached board retrieves, calls LLM,
    interprets routing decisions to select tools, executes tool functions, and structures responses.
    """
    def __init__(self, provider=None, model=None, deals_board_id=None, work_orders_board_id=None):
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self.deals_board_id = deals_board_id or settings.DEALS_BOARD_ID
        self.work_orders_board_id = work_orders_board_id or settings.WORK_ORDERS_BOARD_ID

        # Load correct API Key based on provider configuration
        if self.provider == "openai":
            api_key = settings.OPENAI_API_KEY
        else:
            api_key = settings.ANTHROPIC_API_KEY

        self.llm_client = LLMClient(provider=self.provider, api_key=api_key, model=self.model)
        self.monday_client = MondayClient(api_token=settings.MONDAY_API_TOKEN)
        
        # Proactive directory verification
        os.makedirs(CACHE_DIR, exist_ok=True)

    def get_deals_dataframe(self, force_refresh=False) -> pd.DataFrame:
        """
        Loads Deals from cache if within TTL, else fetches from Monday API and updates cache.
        """
        cache_path = os.path.join(CACHE_DIR, "deals.json")
        
        if not force_refresh and os.path.exists(cache_path):
            mtime = os.path.getmtime(cache_path)
            if time.time() - mtime < CACHE_TTL:
                try:
                    with open(cache_path, "r") as f:
                        raw_data = json.load(f)
                    return normalize_deals(raw_data)
                except Exception as e:
                    logger.warning(f"Error loading deals from cache: {e}. Re-fetching.")

        # Fetch and write cache
        raw_deals = get_deals(self.monday_client, self.deals_board_id)
        try:
            with open(cache_path, "w") as f:
                json.dump(raw_deals, f)
        except Exception as e:
            logger.warning(f"Failed to write deals cache: {e}")

        return normalize_deals(raw_deals)

    def get_work_orders_dataframe(self, force_refresh=False) -> pd.DataFrame:
        """
        Loads Work Orders from cache if within TTL, else fetches from Monday API and updates cache.
        """
        cache_path = os.path.join(CACHE_DIR, "work_orders.json")
        
        if not force_refresh and os.path.exists(cache_path):
            mtime = os.path.getmtime(cache_path)
            if time.time() - mtime < CACHE_TTL:
                try:
                    with open(cache_path, "r") as f:
                        raw_data = json.load(f)
                    return normalize_work_orders(raw_data)
                except Exception as e:
                    logger.warning(f"Error loading work orders from cache: {e}. Re-fetching.")

        # Fetch and write cache
        raw_wo = get_work_orders(self.monday_client, self.work_orders_board_id)
        try:
            with open(cache_path, "w") as f:
                json.dump(raw_wo, f)
        except Exception as e:
            logger.warning(f"Failed to write work orders cache: {e}")

        return normalize_work_orders(raw_wo)

    def answer_query(self, user_query: str) -> dict:
        """
        Translates a human user question, executes agent reasoning loops,
        invokes tool queries, and generates a formatted response containing dataframes.
        """
        try:
            deals_df = self.get_deals_dataframe()
            wo_df = self.get_work_orders_dataframe()
        except Exception as e:
            logger.exception("Failed to pull dataset boards.")
            return {
                "answer": f"⚠️ Connection Error: Failed to pull Monday.com board records: {e}",
                "data": None
            }

        # Format prompt
        user_prompt = f"User Question: {user_query}"
        
        try:
            llm_text = self.llm_client.call_llm(SYSTEM_PROMPT, user_prompt)
            decision = json.loads(llm_text)
        except Exception as e:
            logger.error(f"Error parsing LLM decision. Response content: {llm_text if 'llm_text' in locals() else 'None'}. Error: {e}")
            return {
                "answer": "⚠️ AI Parsing Exception: Could not resolve prompt instructions.",
                "data": None
            }

        tool = decision.get("tool")
        params = decision.get("parameters", {})

        if tool == "final_answer":
            return {
                "answer": params.get("answer", ""),
                "data": None
            }

        # Tool Execution Stage
        result_df = None
        try:
            if tool == "query_deals":
                result_df = tools.query_deals(deals_df)
            elif tool == "query_work_orders":
                result_df = tools.query_work_orders(wo_df)
            elif tool == "join_boards":
                result_df = tools.join_boards(deals_df, wo_df)
            elif tool == "aggregate_metrics":
                result_df = tools.aggregate_metrics(
                    deals_df=deals_df,
                    wo_df=wo_df,
                    dataset=params.get("dataset"),
                    group_by=params.get("group_by"),
                    agg_col=params.get("agg_col"),
                    agg_func=params.get("agg_func")
                )
            else:
                return {
                    "answer": f"⚠️ Unsupported Agent Tool: Assistant requested non-existent tool: {tool}",
                    "data": None
                }
        except Exception as e:
            logger.exception("Failed executing requested tool.")
            return {
                "answer": f"⚠️ Runtime Tool Exception: Error executing tool '{tool}': {e}",
                "data": None
            }

        # Formulate second prompt with results
        data_markdown = result_df.to_markdown(index=False) if not result_df.empty else "No matching items found."
        
        follow_up = f"""User Question: {user_query}

The assistant chose to run tool '{tool}' with parameters: {params}
This successfully returned the following data context:
{data_markdown}

Formulate your final explanation summarizing this data for the user.
Remember to respond ONLY with a JSON object in this format:
{{
  "thought": "Summarizing the final data for the user",
  "tool": "final_answer",
  "parameters": {{
    "answer": "Your markdown summary answer goes here..."
  }}
}}
"""
        try:
            final_text = self.llm_client.call_llm(SYSTEM_PROMPT, follow_up)
            final_decision = json.loads(final_text)
            answer = final_decision.get("parameters", {}).get("answer", "Query completed. Data table displayed below.")
            return {
                "answer": answer,
                "data": result_df
            }
        except Exception as e:
            logger.error(f"Error compiling final answer: {e}. Raw response: {final_text if 'final_text' in locals() else 'None'}")
            return {
                "answer": "Query executed successfully. Resulting table details:",
                "data": result_df
            }
