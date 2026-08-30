from .queries import GET_BOARD_ITEMS
import logging

logger = logging.getLogger(__name__)

def fetch_all_items(client, board_id: str) -> list:
    """
    Fetches all items from a specific Monday.com board by board_id, 
    properly handling pagination cursors.
    """
    if not board_id:
        raise ValueError("board_id is required to fetch items.")

    all_items = []
    cursor = None

    while True:
        variables = {"board_id": board_id}
        if cursor:
            variables["cursor"] = cursor

        response = client.execute_query(GET_BOARD_ITEMS, variables)
        boards = response.get("data", {}).get("boards", [])
        
        if not boards:
            logger.warning(f"No board found with ID: {board_id}")
            break

        items_page = boards[0].get("items_page", {})
        items = items_page.get("items", [])
        all_items.extend(items)

        cursor = items_page.get("cursor")
        if not cursor:
            break

    return all_items

def get_deals(client, board_id: str) -> list:
    """
    Fetches and flat-parses deal items.
    """
    raw_items = fetch_all_items(client, board_id)
    return parse_items_to_flat_dicts(raw_items)

def get_work_orders(client, board_id: str) -> list:
    """
    Fetches and flat-parses work order items.
    """
    raw_items = fetch_all_items(client, board_id)
    return parse_items_to_flat_dicts(raw_items)

def parse_items_to_flat_dicts(items: list) -> list:
    """
    Helper function to turn raw GraphQL deep item response into a flat list of dictionaries
    where each dictionary represents an item and maps column IDs to raw text values.
    """
    parsed = []
    for item in items:
        flat_item = {
            "id": item.get("id"),
            "name": item.get("name")
        }
        for cv in item.get("column_values", []):
            col_id = cv.get("id")
            flat_item[col_id] = cv.get("text")
        parsed.append(flat_item)
    return parsed
