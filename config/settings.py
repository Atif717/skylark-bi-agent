import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from local .env
load_dotenv()


class Settings:
    def __init__(self):
        # Helper to retrieve from os.getenv (local) or st.secrets (Streamlit Cloud)
        def _get(key: str, default: str = "") -> str:
            val = os.getenv(key)
            if val is not None and val.strip() != "":
                return val
            try:
                if key in st.secrets and str(st.secrets[key]).strip() != "":
                    return str(st.secrets[key])
            except Exception:
                pass
            return default

        # Retrieve keys
        self.MONDAY_API_TOKEN = _get("MONDAY_API_TOKEN")
        self.DEALS_BOARD_ID = _get("DEALS_BOARD_ID")
        self.WORK_ORDERS_BOARD_ID = _get("WORK_ORDERS_BOARD_ID")
        
        self.LLM_PROVIDER = _get("LLM_PROVIDER", "openai").lower()
        self.OPENAI_API_KEY = _get("OPENAI_API_KEY")
        self.ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
        self.LLM_MODEL = _get("LLM_MODEL", "gpt-4o")

        # Validation checks
        errors = []
        if not self.MONDAY_API_TOKEN or self.MONDAY_API_TOKEN.strip() == "":
            errors.append("MONDAY_API_TOKEN is missing or empty.")
        if not self.DEALS_BOARD_ID or self.DEALS_BOARD_ID.strip() == "":
            errors.append("DEALS_BOARD_ID is missing or empty.")
        if not self.WORK_ORDERS_BOARD_ID or self.WORK_ORDERS_BOARD_ID.strip() == "":
            errors.append("WORK_ORDERS_BOARD_ID is missing or empty.")
            
        if errors:
            raise ValueError("Configuration Error: " + " | ".join(errors))

    def reload(self):
        """Force reload of environment variables."""
        load_dotenv(override=True)
        self.__init__()


# Expose settings singleton
settings = Settings()