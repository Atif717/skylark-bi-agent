import pandas as pd
from .schema import map_columns, DEALS_SCHEMA, WORK_ORDERS_SCHEMA

def normalize_deals(raw_deals: list) -> pd.DataFrame:
    """
    Takes flat raw deals dictionaries, maps their columns to friendly schemas,
    and normalizes formats (numbers, dates, strings, nulls) into a clean pandas DataFrame.
    """
    mapped = map_columns(raw_deals, DEALS_SCHEMA)
    df = pd.DataFrame(mapped)

    if df.empty:
        # Retain schema shape even if empty
        return pd.DataFrame(columns=["item_id", "name", "status", "value", "close_date", "account_name"])

    # Basic text cleanup
    df["name"] = df["name"].astype(str).str.strip()
    df["status"] = df["status"].astype(str).str.strip().fillna("None").replace("", "None")
    df["account_name"] = df["account_name"].astype(str).str.strip().fillna("None").replace("", "None")

    # Numeric formatting (value should be float)
    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0.0)

    # Date formatting
    df["close_date"] = pd.to_datetime(df["close_date"], errors="coerce")

    return df

def normalize_work_orders(raw_work_orders: list) -> pd.DataFrame:
    """
    Takes flat raw work orders dictionaries, maps their columns to friendly schemas,
    and normalizes formats into a clean pandas DataFrame.
    """
    mapped = map_columns(raw_work_orders, WORK_ORDERS_SCHEMA)
    df = pd.DataFrame(mapped)

    if df.empty:
        # Retain schema shape even if empty
        return pd.DataFrame(columns=["item_id", "name", "status", "priority", "due_date", "deal_name"])

    # Basic text cleanup
    df["name"] = df["name"].astype(str).str.strip()
    df["status"] = df["status"].astype(str).str.strip().fillna("None").replace("", "None")
    df["priority"] = df["priority"].astype(str).str.strip().fillna("None").replace("", "None")
    df["deal_name"] = df["deal_name"].astype(str).str.strip().fillna("None").replace("", "None")

    # Date formatting
    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")

    return df
