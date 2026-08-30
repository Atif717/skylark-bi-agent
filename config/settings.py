import os
from dotenv import load_dotenv

# Load environment variables from .env if it exists
load_dotenv()

class Settings:
    def __init__(self):
        self.MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN", "mock_token")
        self.DEALS_BOARD_ID = os.getenv("DEALS_BOARD_ID", "1234567890")
        self.WORK_ORDERS_BOARD_ID = os.getenv("WORK_ORDERS_BOARD_ID", "0987654321")
        
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "mock_openai_key")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "mock_anthropic_key")
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

    def reload(self):
        """Force reload of environment variables."""
        load_dotenv(override=True)
        self.__init__()

# Expose settings singleton
settings = Settings()
