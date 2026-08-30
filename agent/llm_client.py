import os
import json
import logging
from openai import OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified LLM wrapper to interface with OpenAI and Anthropic client APIs.
    Includes a deterministic mock responder to support testing and offline runs.
    """
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        
        # Determine if we should run in mock mode
        self.is_mock = not api_key or "mock" in api_key.lower() or api_key == "mock_openai_api_key" or api_key == "mock_anthropic_api_key"

        if not self.is_mock:
            if self.provider == "openai":
                self.client = OpenAI(api_key=self.api_key)
            elif self.provider == "anthropic":
                self.client = Anthropic(api_key=self.api_key)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        else:
            logger.info("LLMClient is active in MOCK mode.")

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Executes an LLM message completion request.
        """
        if self.is_mock:
            return self._mock_llm_response(user_prompt)

        if self.provider == "openai":
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI completion request failed: {e}")
                raise RuntimeError(f"OpenAI API Error: {e}")

        elif self.provider == "anthropic":
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0
                )
                return response.content[0].text
            except Exception as e:
                logger.error(f"Anthropic completion request failed: {e}")
                raise RuntimeError(f"Anthropic API Error: {e}")
        else:
            raise ValueError(f"Invalid LLM provider configured: {self.provider}")

    def _mock_llm_response(self, user_prompt: str) -> str:
        """
        Mock agent tool routing based on user input.
        """
        prompt_lower = user_prompt.lower()

        # Step 1: Detect ambiguity (Test agent behavior with intentionally ambiguous queries)
        if "quarter" in prompt_lower and not ("calendar" in prompt_lower or "fiscal" in prompt_lower):
            return json.dumps({
                "thought": "The user referenced 'quarter' without clarifying calendar or fiscal context. I must ask a clarifying question.",
                "tool": "ask_clarifying_question",
                "parameters": {
                    "question": "Could you please clarify if you mean the **calendar quarter** or **fiscal quarter** for this pipeline query?"
                }
            })
            
        if "revenue" in prompt_lower and not any(k in prompt_lower for k in ["billed", "realized", "collected", "received", "receivables"]):
            return json.dumps({
                "thought": "The user requested revenue metrics without specifying billed, collected, or contract value. Asking clarifying question.",
                "tool": "ask_clarifying_question",
                "parameters": {
                    "question": "Are you interested in **billed revenue** (excluding GST), **realized revenue** (collected, including GST), or the **total contract value**?"
                }
            })

        # Step 2: Handle second turn (compiling the final markdown answer with data metrics)
        if "execution_result" in prompt_lower or "data_context" in prompt_lower or "tool_result" in prompt_lower or "stats" in prompt_lower:
            if "stats" in prompt_lower:
                # Leadership Summary response
                return json.dumps({
                    "thought": "Generating leadership final narrative answer.",
                    "tool": "final_answer",
                    "parameters": {
                        "answer": "## Executive Leadership BI Summary\n\n### 📈 Sales Pipeline overview\n- **Total Contract Potential**: **$537.9M** across active deal prospects.\n- **Top Sectors by Pipeline value**:\n  - *Powerline*: $180.1M\n  - *Mining*: $112.9M\n  - *Renewables*: $92.5M\n\n### ⚙️ Operational Project Execution\n- **Work Order Completion rate**: **45.5%** completed (80 out of 176 total active project work orders).\n- **Pending Delivery**: 58 project files remain scheduled for file delivery.\n\n### 💰 Billing & Cash Realization\n- **Total Billed Value**: **$120.4M** (excluding GST).\n- **Total Revenue Collected (Realized)**: **$86.2M** (including GST).\n- **Total Receivables Outstanding**: **$34.2M** outstanding currently.\n\n---\n> ⚠️ *Data Quality Caveat: 10.4% of Deals are missing close dates, and 4.2% of Work Orders have unlinked deal names.*"
                    }
                })
            else:
                # Standard final answer formatting
                return json.dumps({
                    "thought": "Compiling final table explanation.",
                    "tool": "final_answer",
                    "parameters": {
                        "answer": "Here is the filtered result matching your criteria. The requested data has been successfully filtered and displayed below.\n\n*   **Total row matches**: The details are structured and rendered in the data viewer tab.\n*   *Caveat: Some date values in the close_date fields were missing and coerced to NaT.*"
                    }
                })

        # Step 3: Handle first turn routing
        if "leadership" in prompt_lower or "update" in prompt_lower:
            return json.dumps({
                "thought": "User requested leadership summary update. Invoking generate_leadership_summary.",
                "tool": "generate_leadership_summary",
                "parameters": {}
            })
        elif "join" in prompt_lower or "combine" in prompt_lower:
            return json.dumps({
                "thought": "User wants to join Deals and Work Orders. Invoking join_deals_and_orders.",
                "tool": "join_deals_and_orders",
                "parameters": {}
            })
        elif "aggregate" in prompt_lower or "group" in prompt_lower or "sum" in prompt_lower or "total" in prompt_lower:
            dataset = "deals" if "deal" in prompt_lower else "work_orders"
            group_by = "sector" if "sector" in prompt_lower else "deal_status"
            agg_col = "deal_value" if dataset == "deals" else "amount_excl_gst"
            
            return json.dumps({
                "thought": f"User requested aggregation grouping by {group_by}. Invoking aggregate tool.",
                "tool": "aggregate",
                "parameters": {
                    "group_by": group_by,
                    "metric": agg_col,
                    "agg_func": "sum"
                }
            })
        elif "work order" in prompt_lower or "order" in prompt_lower:
            return json.dumps({
                "thought": "Querying work orders board data.",
                "tool": "filter_work_orders",
                "parameters": {
                    "status": "completed" if "completed" in prompt_lower else None
                }
            })
        else:
            # Default helper query
            return json.dumps({
                "thought": "Querying deals list based on user query.",
                "tool": "filter_deals",
                "parameters": {
                    "sector": "Mining" if "mining" in prompt_lower else None,
                    "stage": "Won" if "won" in prompt_lower else None
                }
            })
