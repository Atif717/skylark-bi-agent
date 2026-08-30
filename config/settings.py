import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    def __init__(self):
        # Retrieve keys
        self.MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")
        self.DEALS_BOARD_ID = os.getenv("DEALS_BOARD_ID")
        self.WORK_ORDERS_BOARD_ID = os.getenv("WORK_ORDERS_BOARD_ID")
        
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

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
