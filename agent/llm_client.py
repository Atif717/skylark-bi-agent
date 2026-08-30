import os
import json
import logging
from openai import OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Fallback model list for Groq
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "mixtral-8x7b-32768"
]


class LLMClient:
    """
    Unified LLM wrapper to interface with Groq, OpenAI, and Anthropic client APIs.
    Includes deterministic fallback chains and a mock responder for offline tests.
    """
    def __init__(self, provider: str = "openai", api_key: str = None, model: str = None):
        self.provider = (provider or "openai").lower().strip()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        # Determine if we should run in mock mode
        self.is_mock = (
            not self.api_key
            or "mock" in self.api_key.lower()
            or self.api_key in ("mock_openai_api_key", "mock_anthropic_api_key")
        )

        if not self.is_mock:
            if self.provider == "groq":
                self.model = self.model or "llama-3.3-70b-versatile"
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.groq.com/openai/v1"
                )
            elif self.provider == "openai":
                self.model = self.model or "gpt-4o"
                self.client = OpenAI(api_key=self.api_key)
            elif self.provider == "anthropic":
                self.model = self.model or "claude-3-5-sonnet-20240620"
                self.client = Anthropic(api_key=self.api_key)
            else:
                self.model = self.model or "gpt-4o"
                self.client = OpenAI(api_key=self.api_key)
        else:
            logger.info("LLMClient is active in MOCK mode.")

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Executes an LLM message completion request with automatic model fallback for Groq.
        """
        if self.is_mock:
            return self._mock_llm_response(user_prompt)

        if self.provider == "groq":
            # Try current model, then try remaining models in fallback list
            models_to_try = [self.model] + [m for m in GROQ_MODELS if m != self.model]
            last_err = None
            for m in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=m,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                    self.model = m  # stick with working model
                    return response.choices[0].message.content
                except Exception as e:
                    last_err = e
                    logger.warning(f"Groq model {m} failed: {e}. Trying next fallback...")
                    continue
            raise RuntimeError(f"GROQ API Error: {last_err}")

        elif self.provider == "openai":
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
                logger.error(f"OpenAI API Error: {e}")
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
                logger.error(f"Anthropic API Error: {e}")
                raise RuntimeError(f"Anthropic API Error: {e}")
        else:
            raise ValueError(f"Invalid LLM provider configured: {self.provider}")

    def _mock_llm_response(self, user_prompt: str) -> str:
        prompt_lower = user_prompt.lower()

        if "quarter" in prompt_lower and not ("calendar" in prompt_lower or "fiscal" in prompt_lower):
            return json.dumps({
                "thought": "Clarifying quarter definition.",
                "tool": "ask_clarifying_question",
                "parameters": {
                    "question": "Could you please clarify if you mean the **calendar quarter** or **fiscal quarter** for this pipeline query?"
                }
            })

        if "revenue" in prompt_lower and not any(k in prompt_lower for k in ["billed", "realized", "collected", "received", "receivables"]):
            return json.dumps({
                "thought": "Clarifying revenue metric.",
                "tool": "ask_clarifying_question",
                "parameters": {
                    "question": "Are you interested in **billed revenue** (excluding GST), **realized revenue** (collected, including GST), or the **total contract value**?"
                }
            })

        if any(k in prompt_lower for k in ["leadership", "update", "summary", "brief"]):
            return json.dumps({
                "thought": "User requested leadership summary update.",
                "tool": "generate_leadership_summary",
                "parameters": {}
            })
        elif any(k in prompt_lower for k in ["join", "combine", "linked"]):
            return json.dumps({
                "thought": "User requested cross-board join.",
                "tool": "join_deals_and_orders",
                "parameters": {}
            })
        elif any(k in prompt_lower for k in ["aggregate", "sum", "total"]):
            dataset = "deals" if "deal" in prompt_lower else "work_orders"
            group_by = "sector" if "sector" in prompt_lower else "deal_status"
            agg_col = "deal_value" if dataset == "deals" else "amount_excl_gst"
            return json.dumps({
                "thought": "User requested aggregation.",
                "tool": "aggregate",
                "parameters": {
                    "group_by": group_by,
                    "metric": agg_col,
                    "agg_func": "sum"
                }
            })
        elif any(k in prompt_lower for k in ["work order", "order", "project"]):
            return json.dumps({
                "thought": "Querying work orders.",
                "tool": "filter_work_orders",
                "parameters": {}
            })
        else:
            return json.dumps({
                "thought": "Querying deals list.",
                "tool": "filter_deals",
                "parameters": {
                    "sector": "Mining" if "mining" in prompt_lower else None
                }
            })