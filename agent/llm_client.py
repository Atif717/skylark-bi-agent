import os
import re
import json
import logging
from openai import OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]

# Canonical vocabulary used to extract entities from free text.
# Kept in sync with data_processing.normalizer.normalize_text's canonical output
# and with the status vocabulary described in the system prompt, so filters
# built here always match values that actually exist in the cleaned DataFrames.
SECTOR_CANONICAL = {
    "mining": "Mining", "mine": "Mining",
    "powerline": "Powerline", "power line": "Powerline", "power lines": "Powerline",
    "powerlines": "Powerline", "power": "Powerline",
    "renewables": "Renewables", "renewable": "Renewables", "renew": "Renewables",
    "renewable energy": "Renewables", "energy": "Renewables",
    "railways": "Railways", "railway": "Railways", "rail": "Railways",
    "construction": "Construction", "construct": "Construction",
    "tender": "Tender", "tenders": "Tender",
    "manufacturing": "Manufacturing", "manufacture": "Manufacturing", "manu": "Manufacturing",
    "aviation": "Aviation", "aviations": "Aviation",
    "dsp": "DSP", "dsp services": "DSP",
    "security and surveillance": "Security and Surveillance",
    "surveillance": "Security and Surveillance", "security": "Security and Surveillance",
}

DEAL_STAGE_CANONICAL = {
    "won": "Won", "lost": "Lost", "qualified": "Qualified",
    "proposal": "Proposal", "draft": "Draft", "in progress": "In Progress",
}

WO_STATUS_CANONICAL = {
    "not started": "Not Started",
    "executed until current month": "Executed until current month",
    "partially completed": "Partial Completed",
    "partial completed": "Partial Completed",
    "details pending": "Details pending from Client",
    "pause": "Pause / struck",
    "struck": "Pause / struck",
    "completed": "Completed",
    "ongoing": "Ongoing",
}

QUARTER_WORDS = {
    "first quarter": "1", "1st quarter": "1",
    "second quarter": "2", "2nd quarter": "2",
    "third quarter": "3", "3rd quarter": "3",
    "fourth quarter": "4", "4th quarter": "4",
}

CLARIFYING_MARKERS = (
    "could you please clarify", "clarify if you mean", "are you interested in",
    "clarify the", "which do you mean",
)


def _extract_first_match(text: str, canonical_map: dict) -> str:
    """Returns the canonical value for the first vocabulary hit found in text."""
    for keyword, canonical in canonical_map.items():
        if keyword in text:
            return canonical
    return None


def _extract_quarter(text: str) -> str:
    for phrase, digit in QUARTER_WORDS.items():
        if phrase in text:
            return digit
    match = re.search(r"\bq([1-4])\b", text)
    if match:
        return match.group(1)
    return None


def _sanitize_history(history: list, max_turns: int = 6, max_chars: int = 800) -> list:
    """
    Normalizes a chat history list into a clean, alternating user/assistant
    sequence safe to send to any provider (Anthropic in particular rejects
    consecutive same-role messages and unknown roles).
    """
    if not history:
        return []

    cleaned = []
    for msg in history:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        content = content[:max_chars]
        if cleaned and cleaned[-1]["role"] == role:
            # Merge consecutive same-role turns instead of dropping information.
            cleaned[-1]["content"] += "\n" + content
        else:
            cleaned.append({"role": role, "content": content})

    # Trim to the most recent N turns, but make sure we still start on "user"
    # (Anthropic requires the first message in the list to be role "user").
    cleaned = cleaned[-max_turns:]
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    return cleaned


class LLMClient:
    """
    Unified LLM wrapper to interface with Groq, OpenAI, and Anthropic client APIs.
    Includes active production model lists, conversation-history-aware calls,
    and a deterministic rule-based fallback for when no provider is reachable.
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
                self.model = self.model if (self.model and "llama" in self.model) else "llama-3.3-70b-versatile"
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

    def call_llm(self, system_prompt: str, user_prompt: str, history: list = None) -> str:
        """
        Executes an LLM message completion request with graceful fallback.

        `history` is an optional list of {"role": "user"|"assistant", "content": str}
        dicts representing prior turns in the conversation (most recent last, NOT
        including the current `user_prompt`). Passing this lets the model resolve
        follow-ups and answers to its own earlier clarifying questions instead of
        treating every message as a brand-new, context-free query.
        """
        history = _sanitize_history(history)

        if self.is_mock:
            return self._mock_llm_response(user_prompt, history)

        sys_prompt = system_prompt
        if "json" not in sys_prompt.lower():
            sys_prompt += "\nRespond strictly in JSON format."

        if self.provider == "groq":
            models_to_try = [self.model] + [m for m in GROQ_MODELS if m != self.model]
            for m in models_to_try:
                try:
                    messages = [{"role": "system", "content": sys_prompt}] + history + \
                        [{"role": "user", "content": user_prompt}]
                    response = self.client.chat.completions.create(
                        model=m,
                        messages=messages,
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                    self.model = m
                    return response.choices[0].message.content
                except Exception as e:
                    logger.warning(f"Groq model {m} attempt failed: {e}")
                    continue

            logger.warning("All Groq endpoints failed. Falling back to internal agent rules.")
            return self._mock_llm_response(user_prompt, history)

        elif self.provider == "openai":
            try:
                messages = [{"role": "system", "content": sys_prompt}] + history + \
                    [{"role": "user", "content": user_prompt}]
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"OpenAI call failed ({e}). Using rule fallback.")
                return self._mock_llm_response(user_prompt, history)

        elif self.provider == "anthropic":
            try:
                messages = history + [{"role": "user", "content": user_prompt}]
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=sys_prompt,
                    messages=messages,
                    temperature=0.0
                )
                return response.content[0].text
            except Exception as e:
                logger.warning(f"Anthropic call failed ({e}). Using rule fallback.")
                return self._mock_llm_response(user_prompt, history)
        else:
            return self._mock_llm_response(user_prompt, history)

    def _mock_llm_response(self, user_prompt: str, history: list = None) -> str:
        """
        Deterministic, keyword-driven fallback used when no LLM provider is
        reachable (missing key, rate limit, network failure). It is intentionally
        conversation-aware: it looks back over prior user turns so a filter
        mentioned earlier in the chat isn't lost, and it recognizes when the
        current message is answering its own previous clarifying question so it
        doesn't ask the same thing twice.
        """
        history = history or []
        current_lower = user_prompt.lower()

        prior_user_turns = [m["content"].lower() for m in history if m.get("role") == "user"]
        last_assistant_turn = ""
        for m in reversed(history):
            if m.get("role") == "assistant":
                last_assistant_turn = m["content"].lower()
                break

        was_asked_clarifying_question = any(marker in last_assistant_turn for marker in CLARIFYING_MARKERS)

        # Combine current message with recent prior user turns so context (sector,
        # stage, etc. mentioned earlier) survives across a clarification round-trip.
        combined_text = " ".join(prior_user_turns[-4:] + [current_lower])

        # --- Step 1: Ambiguity checks (skip if we already asked once this thread) ---
        if not was_asked_clarifying_question:
            if "quarter" in combined_text and not any(k in combined_text for k in ("calendar", "fiscal")):
                return json.dumps({
                    "thought": "Clarifying quarter definition.",
                    "tool": "ask_clarifying_question",
                    "parameters": {
                        "question": "Could you please clarify if you mean the **calendar quarter** or **fiscal quarter** for this pipeline query?"
                    }
                })

            if "revenue" in combined_text and not any(
                k in combined_text for k in ("billed", "realized", "collected", "received", "receivables")
            ):
                return json.dumps({
                    "thought": "Clarifying revenue metric.",
                    "tool": "ask_clarifying_question",
                    "parameters": {
                        "question": "Are you interested in **billed revenue** (excluding GST), **realized revenue** (collected, including GST), or the **total contract value**?"
                    }
                })

        # --- Step 2: Summary / Executive update matches ---
        if any(k in combined_text for k in ["summarize", "summary", "leadership", "update", "overview", "brief", "report"]):
            return json.dumps({
                "thought": "User requested executive leadership summary update.",
                "tool": "generate_leadership_summary",
                "parameters": {}
            })

        sector = _extract_first_match(combined_text, SECTOR_CANONICAL)
        quarter = _extract_quarter(combined_text)

        # --- Step 3: Joins ---
        if any(k in combined_text for k in ["join", "combine", "linked", "connected"]):
            params = {}
            if sector:
                params["sector"] = sector
            if "ongoing" in combined_text or "in progress" in combined_text:
                params["execution_status"] = "Ongoing"
            elif "completed" in combined_text:
                params["execution_status"] = "Completed"
            if "open" in combined_text:
                params["deal_status"] = "Open"
            return json.dumps({
                "thought": "User requested cross-board join.",
                "tool": "join_deals_and_orders",
                "parameters": params
            })

        # --- Step 4: Aggregation (use \b to avoid matching "summarize") ---
        if re.search(r"\b(sum|total|aggregate|average|mean)\b", combined_text):
            is_wo_metric = any(
                k in combined_text for k in ["work order", "execution", "billed", "collected", "amount", "gst", "receivable"]
            )
            dataset = "work_orders" if is_wo_metric else "deals"

            if dataset == "deals":
                group_by = "sector" if sector or "sector" in combined_text else "deal_status"
                metric = "deal_value"
            else:
                group_by = "sector" if sector or "sector" in combined_text else "execution_status"
                metric = "amount_excl_gst"
                if "collected" in combined_text:
                    metric = "collected_incl_gst"
                elif "billed" in combined_text:
                    metric = "billed_excl_gst"

            return json.dumps({
                "thought": "User requested numeric aggregation.",
                "tool": "aggregate",
                "parameters": {
                    "group_by": group_by,
                    "metric": metric,
                    "agg_func": "sum"
                }
            })

        # --- Step 5: Work Orders vs Deals filtering ---
        if any(k in combined_text for k in ["work order", "order", "project", "execution"]):
            wo_status = _extract_first_match(combined_text, WO_STATUS_CANONICAL)
            params = {}
            if wo_status:
                params["status"] = wo_status
            if sector:
                params["sector"] = sector
            return json.dumps({
                "thought": "Querying work orders.",
                "tool": "filter_work_orders",
                "parameters": params
            })

        stage = _extract_first_match(combined_text, DEAL_STAGE_CANONICAL)
        params = {}
        if sector:
            params["sector"] = sector
        if stage:
            params["stage"] = stage
        if quarter:
            params["quarter"] = f"Q{quarter}"

        return json.dumps({
            "thought": "Querying deals list.",
            "tool": "filter_deals",
            "parameters": params
        })