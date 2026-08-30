# Schema column-name mappings (Monday raw column IDs -> human-friendly names)

DEALS_SCHEMA = {
    "deal_status": "status",
    "deal_value": "value",
    "close_date": "close_date",
    "account_name": "account_name"
}

WORK_ORDERS_SCHEMA = {
    "wo_status": "status",
    "wo_priority": "priority",
    "due_date": "due_date",
    "deal_link": "deal_name"
}

def map_columns(items: list, schema: dict) -> list:
    """
    Translates raw Monday.com item dictionaries with API column IDs
    into clean dictionaries using friendly names from the schema.
    """
    mapped_items = []
    for item in items:
        mapped = {
            "item_id": item.get("id"),
            "name": item.get("name")
        }
        # Iterate over other raw fields in the flat item dict
        for raw_key, value in item.items():
            if raw_key in ("id", "name"):
                continue
            # Map raw key to friendly key if mapping exists
            friendly_key = schema.get(raw_key, raw_key)
            mapped[friendly_key] = value
        mapped_items.append(mapped)
    return mapped_items
