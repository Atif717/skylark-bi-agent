import os
import json
import time
import pandas as pd
import logging
from config.settings import settings
from monday_client.client import MondayClient
from monday_client.fetch import get_deals, get_work_orders
from data_processing.normalizer import normalize_deals, normalize_work_orders
from data_processing.quality import check_data_quality
from .llm_client import LLMClient
from .prompts import SYSTEM_PROMPT
from . import tools

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
CACHE_TTL = 300  # Cache TTL: 5 minutes

class AgentOrchestrator:
    """
    Coordinates data fetching, cleaning, LLM instruction routing, tool execution,
    and compiling final natural language answers with warnings.
    """
    def __init__(self, provider=None, model=None, deals_board_id=None, work_orders_board_id=None):
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self.deals_board_id = deals_board_id or settings.DEALS_BOARD_ID
        self.work_orders_board_id = work_orders_board_id or settings.WORK_ORDERS_BOARD_ID

        # Choose correct API Key based on provider configuration
        if self.provider == "openai":
            api_key = settings.OPENAI_API_KEY
        else:
            api_key = settings.ANTHROPIC_API_KEY

        self.llm_client = LLMClient(provider=self.provider, api_key=api_key, model=self.model)
        self.monday_client = MondayClient(api_token=settings.MONDAY_API_TOKEN)
        
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
                    logger.warning(f"Error loading deals cache: {e}. Re-fetching.")

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
                    logger.warning(f"Error loading work orders cache: {e}. Re-fetching.")

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
        Processes a user query by coordinating LLM planning, executing tools,
        and generating a final response with warnings.
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

        # Generate data quality checks
        deals_quality = check_data_quality(deals_df, "Deals Board")
        wo_quality = check_data_quality(wo_df, "Work Orders Board")

        user_prompt = f"User Question: {user_query}"
        
        try:
            llm_text = self.llm_client.call_llm(SYSTEM_PROMPT, user_prompt)
            decision = json.loads(llm_text)
        except Exception as e:
            logger.error(f"Error parsing LLM decision. Response: {llm_text if 'llm_text' in locals() else 'None'}. Error: {e}")
            return {
                "answer": "⚠️ AI Parsing Exception: Could not resolve query formatting instruction.",
                "data": None
            }

        tool = decision.get("tool")
        params = decision.get("parameters", {})

        # Handle clarifying questions directly (Step 6 requirement)
        if tool == "ask_clarifying_question":
            return {
                "answer": params.get("question", "Could you please clarify your request?"),
                "is_clarifying": True,
                "data": None
            }

        if tool == "final_answer":
            return {
                "answer": params.get("answer", ""),
                "data": None
            }

        # Tool Execution Stage
        result_df = None
        caveats = "None flagged."
        
        try:
            if tool == "filter_deals":
                res = tools.filter_deals(deals_df, deals_quality["reports"], **params)
                result_df = res["data"]
                caveats = res["caveats"]
            elif tool == "filter_work_orders":
                res = tools.filter_work_orders(wo_df, wo_quality["reports"], **params)
                result_df = res["data"]
                caveats = res["caveats"]
            elif tool == "join_deals_and_orders":
                res = tools.join_deals_and_orders(deals_df, wo_df, deals_quality["reports"], wo_quality["reports"])
                result_df = res["data"]
                caveats = res["caveats"]
            elif tool == "aggregate":
                # Determine which board to aggregate
                group_col = params.get("group_by", "")
                metric_col = params.get("metric", "")
                
                # Check column mapping
                if group_col in deals_df.columns or metric_col in deals_df.columns:
                    target_df = deals_df
                    target_reports = deals_quality["reports"]
                else:
                    target_df = wo_df
                    target_reports = wo_quality["reports"]
                    
                res = tools.aggregate(
                    df=target_df,
                    quality_reports=target_reports,
                    group_by=group_col,
                    metric=metric_col,
                    agg_func=params.get("agg_func", "sum")
                )
                result_df = res["data"]
                caveats = res["caveats"]
            elif tool == "generate_leadership_summary":
                # Compute leadership stats
                res = tools.generate_leadership_summary(deals_df, wo_df, deals_quality["reports"], wo_quality["reports"])
                stats_summary = json.dumps(res["stats"], indent=2)
                caveats = res["caveats"]
                
                # Render leadership executive markdown via second LLM call
                follow_up = f"""User Question: {user_query}
                
Here are the raw business statistics for this week's leadership update:
{stats_summary}

Please draft a concise, executive-ready narrative report based on these stats.
Include pipelines by sector, completion rates, and billings vs collections.

Respond ONLY with a JSON object in this format:
{{
  "thought": "Writing executive summary report",
  "tool": "final_answer",
  "parameters": {{
    "answer": "Your executive markdown text report goes here..."
  }}
}}
"""
                final_text = self.llm_client.call_llm(SYSTEM_PROMPT, follow_up)
                final_decision = json.loads(final_text)
                answer = final_decision.get("parameters", {}).get("answer", "Leadership summary failed.")
                
                # Optionally, return pipeline sector df as display table
                display_df = pd.DataFrame(res["stats"]["pipeline_by_sector"]) if res["stats"]["pipeline_by_sector"] else None
                
                # Append warnings directly to answer
                if caveats:
                    answer += f"\n\n---\n> ⚠️ *{caveats}*"
                    
                return {
                    "answer": answer,
                    "data": display_df
                }
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

        # Ask LLM for the final narrative explanation, including the executed data's markdown and caveats
        data_markdown = result_df.to_markdown(index=False) if not result_df.empty else "No matching items found."
        
        follow_up = f"""User Question: {user_query}

The assistant chose to run tool '{tool}' with parameters: {params}
This successfully returned the following data context:
{data_markdown}

Quality Warning Caveats: {caveats}

Formulate your final explanation summarizing this data for the user.
Mention the data quality caveats explicitly in your report.
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
            
            # Append caveats to the response if not already present
            if caveats and caveats not in answer:
                answer += f"\n\n---\n> ⚠️ *{caveats}*"
                
            return {
                "answer": answer,
                "data": result_df
            }
        except Exception as e:
            logger.error(f"Error compiling final answer: {e}. Raw response: {final_text if 'final_text' in locals() else 'None'}")
            return {
                "answer": f"Query executed successfully. Resulting table details:\n\n*Caveats: {caveats}*",
                "data": result_df
            }
class InSessionCache:
    """
    Session-level cache wrapper to prevent duplicate API fetches during a chat session.
    """
    @staticmethod
    def get_dataframes(orchestrator: AgentOrchestrator, force_refresh=False):
        import streamlit as st
        if "deals_df" not in st.session_state or "wo_df" not in st.session_state or force_refresh:
            st.session_state["deals_df"] = orchestrator.get_deals_dataframe(force_refresh=force_refresh)
            st.session_state["wo_df"] = orchestrator.get_work_orders_dataframe(force_refresh=force_refresh)
        return st.session_state["deals_df"], st.session_state["wo_df"]
