import os
import json
import logging
from openai import OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified LLM wrapper to interface with OpenAI and Anthropic client APIs.
    Includes a deterministic mockup generator to support offline developer workflow.
    """
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        
        # Determine if we should run in mock mode
        self.is_mock = "mock" in api_key.lower() or not api_key

        if not self.is_mock:
            if self.provider == "openai":
                self.client = OpenAI(api_key=self.api_key)
            elif self.provider == "anthropic":
                self.client = Anthropic(api_key=self.api_key)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        else:
            logger.info("Initializing LLMClient in MOCK mode.")

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Executes an LLM chat/message completion request, enforcing standard formatting.
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
                logger.error(f"OpenAI request failed: {e}")
                raise RuntimeError(f"OpenAI API Error: {e}")

        elif self.provider == "anthropic":
            try:
                # Prompt engineering detail: System prompt passed explicitly to Anthropic client
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
                logger.error(f"Anthropic request failed: {e}")
                raise RuntimeError(f"Anthropic API Error: {e}")
        else:
            raise ValueError(f"Invalid LLM provider configured: {self.provider}")

    def _mock_llm_response(self, user_prompt: str) -> str:
        """
        Mock agent tool routing based on user input.
        """
        prompt_lower = user_prompt.lower()

        # If this is the second turn (it has execution results or table records inside it)
        if "execution_result" in prompt_lower or "data_context" in prompt_lower:
            if "acme" in prompt_lower or "won" in prompt_lower or "deal" in prompt_lower:
                return json.dumps({
                    "thought": "I have retrieved the board information. Now presenting final summary.",
                    "tool": "final_answer",
                    "parameters": {
                        "answer": "### Board Data Summary\n\n**Deals Board Overview:**\n"
                                  "- **Total Deals**: 5\n"
                                  "- **Total Value**: $660,000 (Acme Corp Expansion: $120k, Umbrella Corp Licensing: $350k, Globex CRM Setup: $45k, Initech: $85k, Veerdyne: $60k)\n"
                                  "- **Won Deals**: Acme Corp Expansion ($120k) and Umbrella Corp Licensing ($350k)\n\n"
                                  "**Work Orders Board Overview:**\n"
                                  "- **Total Work Orders**: 4\n"
                                  "- **In Progress**: 2 (Acme Deployment, Umbrella Support Ticket)\n"
                                  "- **Completed**: 1 (Umbrella Initial Rollout)\n"
                                  "- **Pending**: 1 (Globex Provisioning)"
                    }
                })
            else:
                return json.dumps({
                    "thought": "Formatting general response response.",
                    "tool": "final_answer",
                    "parameters": {
                        "answer": "Here is the summary of the metrics based on current board records. You can see detailed status and breakdowns in the preview tabs."
                    }
                })

        # If it is the first turn, pick a tool to call
        if "join" in prompt_lower or "combine" in prompt_lower or ("work order" in prompt_lower and "deal" in prompt_lower):
            return json.dumps({
                "thought": "User wants to join Deals and Work Orders. I will invoke join_boards tool.",
                "tool": "join_boards",
                "parameters": {}
            })
        elif "aggregate" in prompt_lower or "group" in prompt_lower or "sum" in prompt_lower or "total" in prompt_lower:
            dataset = "deals" if "deal" in prompt_lower else "work_orders"
            group_by = "status" if "status" in prompt_lower else "priority"
            agg_col = "value" if dataset == "deals" else "item_id"
            agg_func = "sum" if ("sum" in prompt_lower or "total" in prompt_lower) and dataset == "deals" else "count"
            
            return json.dumps({
                "thought": f"User requested group analysis on {dataset}. I will call aggregate_metrics.",
                "tool": "aggregate_metrics",
                "parameters": {
                    "dataset": dataset,
                    "group_by": group_by,
                    "agg_col": agg_col,
                    "agg_func": agg_func
                }
            })
        elif "work order" in prompt_lower or "priority" in prompt_lower or "due" in prompt_lower:
            return json.dumps({
                "thought": "User asking about Work Orders. I will invoke query_work_orders.",
                "tool": "query_work_orders",
                "parameters": {}
            })
        else:
            # Default helper query
            return json.dumps({
                "thought": "Querying deals list as default strategy.",
                "tool": "query_deals",
                "parameters": {}
            })
