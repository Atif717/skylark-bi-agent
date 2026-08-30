import os
import re
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


def _parse_llm_json(raw_text: str) -> dict:
    """
    Safely extracts and parses JSON even if wrapped in markdown code fences
    or preceded/followed by conversational filler.
    """
    if not raw_text or not isinstance(raw_text, str):
        return {}

    text = raw_text.strip()

    # Strip markdown ```json ... ``` blocks
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()

    # Direct JSON parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Regex search for first outer JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return {}


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

        # Choose API Key based on provider
        if self.provider == "openai":
            api_key = settings.OPENAI_API_KEY
        elif self.provider == "groq":
            api_key = settings.OPENAI_API_KEY  # or groq key passed via env/secrets
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
                    with open(cache_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                    return normalize_deals(raw_data)
                except Exception as e:
                    logger.warning(f"Error loading deals cache: {e}. Re-fetching.")

        # Fetch and write cache
        raw_deals = get_deals(self.monday_client, self.deals_board_id)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
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
                    with open(cache_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                    return normalize_work_orders(raw_data)
                except Exception as e:
                    logger.warning(f"Error loading work orders cache: {e}. Re-fetching.")

        # Fetch and write cache
        raw_wo = get_work_orders(self.monday_client, self.work_orders_board_id)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
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
            decision = _parse_llm_json(llm_text)
            
            if not decision:
                # Fallback rule-based matching if LLM quota exceeded or invalid response
                q_lower = user_query.lower().strip()
                if any(k in q_lower for k in ["summarize", "summary", "leadership", "update", "brief", "overview", "report"]):
                    decision = {"tool": "generate_leadership_summary", "parameters": {}}
                elif any(k in q_lower for k in ["join", "linked", "connected", "combine"]):
                    decision = {"tool": "join_deals_and_orders", "parameters": {}}
                elif bool(re.search(r"\b(sum|total|aggregate|average|mean)\b", q_lower)):
                    decision = {"tool": "aggregate", "parameters": {"group_by": "sector", "metric": "deal_value"}}
                elif any(k in q_lower for k in ["work order", "execution", "project", "order"]):
                    decision = {"tool": "filter_work_orders", "parameters": {}}
                else:
                    decision = {"tool": "filter_deals", "parameters": {}}
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return {
                "answer": f"⚠️ LLM API Error: {e}. Please check your API quota or provider settings.",
                "data": None
            }

        tool = decision.get("tool")
        params = decision.get("parameters", {})

        # Handle clarifying questions directly
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
                res = tools.join_deals_and_orders(deals_df, wo_df, deals_quality["reports"], wo_quality["reports"], **params)
                result_df = res["data"]
                caveats = res["caveats"]
            elif tool == "aggregate":
                group_col = params.get("group_by", "sector")
                metric_col = params.get("metric", "deal_value")
                
                # Check metric and group column availability across datasets
                if metric_col in wo_df.columns:
                    target_df = wo_df
                    target_reports = wo_quality["reports"]
                    if group_col not in wo_df.columns:
                        group_col = "sector" if "sector" in wo_df.columns else "execution_status"
                elif metric_col in deals_df.columns:
                    target_df = deals_df
                    target_reports = deals_quality["reports"]
                    if group_col not in deals_df.columns:
                        group_col = "sector" if "sector" in deals_df.columns else "deal_status"
                elif group_col in deals_df.columns:
                    target_df = deals_df
                    target_reports = deals_quality["reports"]
                    metric_col = "deal_value"
                else:
                    target_df = wo_df
                    target_reports = wo_quality["reports"]
                    metric_col = "amount_excl_gst"
                    
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
                res = tools.generate_leadership_summary(deals_df, wo_df, deals_quality["reports"], wo_quality["reports"])
                stats = res["stats"]
                caveats = res["caveats"]
                
                top_sectors = "\n".join([f"- **{r.get('sector', 'Unknown')}**: ${r.get('deal_value', 0):,.2f}" for r in stats.get("pipeline_by_sector", [])[:3]])
                
                summary_narrative = (
                    f"### 📈 Executive Leadership BI Summary\n\n"
                    f"#### 💼 Sales Pipeline Overview\n"
                    f"- **Total Pipeline Value**: ${stats.get('total_deals_value', 0):,.2f} across {stats.get('total_deals_count', 0)} active deals.\n"
                    f"- **Top Sectors by Pipeline**:\n{top_sectors}\n\n"
                    f"#### ⚙️ Operational Project Execution\n"
                    f"- **Work Order Completion Rate**: {stats.get('work_order_completion_rate', 'N/A')}\n"
                    f"- **Total Tracked Work Orders**: {stats.get('total_work_orders', 0)}\n\n"
                    f"#### 💵 Billing & Cash Realization\n"
                    f"- **Total Billed (Excl. GST)**: ${stats.get('revenue_billed_excl_gst', 0):,.2f}\n"
                    f"- **Total Collected (Incl. GST)**: ${stats.get('revenue_collected_incl_gst', 0):,.2f}"
                )
                
                if caveats:
                    summary_narrative += f"\n\n---\n> ⚠️ *{caveats}*"
                    
                display_df = pd.DataFrame(stats["pipeline_by_sector"]) if stats.get("pipeline_by_sector") else None
                return {
                    "answer": summary_narrative,
                    "data": display_df
                }
            else:
                return {
                    "answer": f"⚠️ Unsupported Agent Tool: {tool}",
                    "data": None
                }
        except Exception as e:
            logger.exception("Failed executing requested tool.")
            return {
                "answer": f"⚠️ Runtime Tool Exception: Error executing tool '{tool}': {e}",
                "data": None
            }

        # Build clean final answer
        answer = "Query completed. Data table displayed below."
        if caveats and caveats not in answer:
            answer += f"\n\n---\n> ⚠️ *{caveats}*"
            
        return {
            "answer": answer,
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