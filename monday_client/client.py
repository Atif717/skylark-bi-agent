import requests
import logging

logger = logging.getLogger(__name__)

class MondayClient:
    """
    A thin, native GraphQL client for interfacing with Monday.com's API.
    """
    API_URL = "https://api.monday.com/v2"

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-01"  # API Version constraint
        }

    def execute_query(self, query: str, variables: dict = None) -> dict:
        """
        Executes a GraphQL query/mutation on Monday.com.
        """
        # If API token is a mock token, return mock responses for development
        if "mock" in self.api_token.lower() or not self.api_token:
            return self._get_mock_response(query, variables)

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(self.API_URL, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "errors" in data:
                logger.error(f"GraphQL Errors: {data['errors']}")
                raise ValueError(f"GraphQL Error: {data['errors'][0]['message']}")
                
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error executing Monday.com query: {e}")
            raise RuntimeError(f"Monday.com Connection Error: {e}")

    def _get_mock_response(self, query: str, variables: dict = None) -> dict:
        """
        Generates clean mock responses to allow offline running and robust testing.
        """
        # Identify board id in query or variables
        board_id = variables.get("board_id") if variables else None
        
        # Determine query type (deals vs work orders) based on query content or variables
        is_deals = False
        is_work_orders = False
        
        # If it asks for a specific board ID, use it to distinguish
        if board_id:
            board_id_str = str(board_id)
            if "1234567890" in board_id_str:
                is_deals = True
            elif "0987654321" in board_id_str:
                is_work_orders = True
        
        # Fallback keyword checks if no board_id matched
        if not (is_deals or is_work_orders):
            if "deal" in query.lower():
                is_deals = True
            else:
                is_work_orders = True

        if is_deals:
            return {
                "data": {
                    "boards": [{
                        "id": "1234567890",
                        "name": "Deals Board",
                        "items_page": {
                            "cursor": None,
                            "items": [
                                {
                                    "id": "item_d1",
                                    "name": "Acme Corp Expansion",
                                    "column_values": [
                                        {"id": "deal_status", "text": "Won", "value": "{\"index\": 1}"},
                                        {"id": "deal_value", "text": "120000", "value": "120000"},
                                        {"id": "close_date", "text": "2026-08-15", "value": "{\"date\": \"2026-08-15\"}"},
                                        {"id": "account_name", "text": "Acme Corp", "value": "Acme Corp"}
                                    ]
                                },
                                {
                                    "id": "item_d2",
                                    "name": "Globex CRM Setup",
                                    "column_values": [
                                        {"id": "deal_status", "text": "Proposal", "value": "{\"index\": 0}"},
                                        {"id": "deal_value", "text": "45000", "value": "45000"},
                                        {"id": "close_date", "text": "2026-09-10", "value": "{\"date\": \"2026-09-10\"}"},
                                        {"id": "account_name", "text": "Globex Inc", "value": "Globex Inc"}
                                    ]
                                },
                                {
                                    "id": "item_d3",
                                    "name": "Initech Integration",
                                    "column_values": [
                                        {"id": "deal_status", "text": "Qualified", "value": "{\"index\": 2}"},
                                        {"id": "deal_value", "text": "85000", "value": "85000"},
                                        {"id": "close_date", "text": "", "value": None},
                                        {"id": "account_name", "text": "Initech", "value": "Initech"}
                                    ]
                                },
                                {
                                    "id": "item_d4",
                                    "name": "Umbrella Corp Licensing",
                                    "column_values": [
                                        {"id": "deal_status", "text": "Won", "value": "{\"index\": 1}"},
                                        {"id": "deal_value", "text": "350000", "value": "350000"},
                                        {"id": "close_date", "text": "2026-07-22", "value": "{\"date\": \"2026-07-22\"}"},
                                        {"id": "account_name", "text": "Umbrella Corp", "value": "Umbrella Corp"}
                                    ]
                                },
                                {
                                    "id": "item_d5",
                                    "name": "Veerdyne Tech Migration",
                                    "column_values": [
                                        {"id": "deal_status", "text": "Lost", "value": "{\"index\": 3}"},
                                        {"id": "deal_value", "text": "60000", "value": "60000"},
                                        {"id": "close_date", "text": "2026-08-01", "value": "{\"date\": \"2026-08-01\"}"},
                                        {"id": "account_name", "text": "Veerdyne", "value": "Veerdyne"}
                                    ]
                                }
                            ]
                        }
                    }]
                }
            }
        else:
            return {
                "data": {
                    "boards": [{
                        "id": "0987654321",
                        "name": "Work Orders Board",
                        "items_page": {
                            "cursor": None,
                            "items": [
                                {
                                    "id": "item_w1",
                                    "name": "Acme Deployment",
                                    "column_values": [
                                        {"id": "wo_status", "text": "In Progress", "value": "{\"index\": 1}"},
                                        {"id": "wo_priority", "text": "High", "value": "{\"index\": 2}"},
                                        {"id": "due_date", "text": "2026-09-05", "value": "{\"date\": \"2026-09-05\"}"},
                                        {"id": "deal_link", "text": "Acme Corp Expansion", "value": "Acme Corp Expansion"}
                                    ]
                                },
                                {
                                    "id": "item_w2",
                                    "name": "Globex Provisioning",
                                    "column_values": [
                                        {"id": "wo_status", "text": "Pending", "value": "{\"index\": 0}"},
                                        {"id": "wo_priority", "text": "Medium", "value": "{\"index\": 1}"},
                                        {"id": "due_date", "text": "2026-09-30", "value": "{\"date\": \"2026-09-30\"}"},
                                        {"id": "deal_link", "text": "Globex CRM Setup", "value": "Globex CRM Setup"}
                                    ]
                                },
                                {
                                    "id": "item_w3",
                                    "name": "Umbrella Initial Rollout",
                                    "column_values": [
                                        {"id": "wo_status", "text": "Completed", "value": "{\"index\": 2}"},
                                        {"id": "wo_priority", "text": "High", "value": "{\"index\": 2}"},
                                        {"id": "due_date", "text": "2026-08-10", "value": "{\"date\": \"2026-08-10\"}"},
                                        {"id": "deal_link", "text": "Umbrella Corp Licensing", "value": "Umbrella Corp Licensing"}
                                    ]
                                },
                                {
                                    "id": "item_w4",
                                    "name": "Umbrella Support Ticket",
                                    "column_values": [
                                        {"id": "wo_status", "text": "In Progress", "value": "{\"index\": 1}"},
                                        {"id": "wo_priority", "text": "Low", "value": "{\"index\": 0}"},
                                        {"id": "due_date", "text": "2026-09-01", "value": "{\"date\": \"2026-09-01\"}"},
                                        {"id": "deal_link", "text": "Umbrella Corp Licensing", "value": "Umbrella Corp Licensing"}
                                    ]
                                }
                            ]
                        }
                    }]
                }
            }
