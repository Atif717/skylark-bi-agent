import re
import pandas as pd
from typing import Any, List, Dict
from .schema import map_columns, DEALS_SCHEMA, WORK_ORDERS_SCHEMA


def parse_date_flexible(val: Any) -> Any:
    """
    Parses dates flexibly, supporting standard formats, pandas timestamps,
    and handles missing/invalid date values.
    """
    if pd.isna(val) or val is None:
        return pd.NaT
    val_str = str(val).strip()
    # Check for empty placeholders or header string leaks
    if not val_str or val_str.lower() in (
        "nan", "none", "null", "nat", "created date", "close date (a)",
        "tentative close date", "date of po/loi", "probable start date",
        "probable end date", "last invoice date", "data delivery date"
    ):
        return pd.NaT

    try:
        return pd.to_datetime(val_str, errors="coerce")
    except Exception:
        return pd.NaT


def normalize_text(val: Any) -> str:
    """
    Cleans text: trims whitespace, handles casing, maps known sector/service variations.
    """
    if pd.isna(val) or val is None:
        return "None"
    val_str = str(val).strip()
    if not val_str or val_str.lower() in (
        "nan", "none", "null", "nat", "unnamed: 0", "sector/service",
        "deal name", "owner code", "client code", "deal status",
        "deal stage", "product deal", "created date"
    ):
        return "None"

    # Map sector / category variations
    val_lower = val_str.lower()
    if val_lower in ("power", "powerline", "powerlines", "power line", "power lines"):
        return "Powerline"
    elif val_lower in ("renew", "renewables", "renewable"):
        return "Renewables"
    elif val_lower in ("rail", "railways", "railway"):
        return "Railways"
    elif val_lower in ("construct", "construction"):
        return "Construction"
    elif val_lower in ("mine", "mining"):
        return "Mining"
    elif val_lower in ("tender", "tenders"):
        return "Tender"
    elif val_lower in ("manu", "manufacturing"):
        return "Manufacturing"
    elif val_lower in ("aviation", "aviations"):
        return "Aviation"
    elif val_lower in ("dsp", "dsp services"):
        return "DSP"

    return val_str


def coerce_number(val: Any) -> float:
    """
    Strips currency prefixes (Rs., $, INR), commas, and spaces, then extracts float.
    """
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null", "nat", "masked deal value", "amount"):
        return 0.0

    # Remove currency text prefixes explicitly (handling with/without dot)
    val_str = re.sub(r'(?i)\b(inr|usd)\b', '', val_str)
    val_str = re.sub(r'(?i)rs\.?', '', val_str)
    val_str = re.sub(r'[\$,₹€]', '', val_str).strip()

    # Remove commas
    val_str = val_str.replace(",", "")

    # Extract clean number (optional negative sign, digits, optional single decimal)
    match = re.search(r'[-+]?\d+(?:\.\d+)?', val_str)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return 0.0
    return 0.0


def normalize_deals(raw_deals: list) -> pd.DataFrame:
    """
    Translates, normalizes, and filters Deals records.
    Filters out repeated header rows and safely applies transformations.
    """
    mapped = map_columns(raw_deals, DEALS_SCHEMA)
    df = pd.DataFrame(mapped)

    if df.empty:
        return pd.DataFrame(columns=[
            "item_id", "name", "owner_code", "client_code", "deal_status",
            "close_date", "closure_probability", "deal_value",
            "tentative_close_date", "deal_stage", "product", "sector", "created_date"
        ])

    # Filter out repeated header row leaks if present
    if "name" in df.columns:
        df = df[df["name"].astype(str).str.lower() != "deal name"]
    if "sector" in df.columns:
        df = df[df["sector"].astype(str).str.lower() != "sector/service"]
    if "deal_status" in df.columns:
        df = df[df["deal_status"].astype(str).str.lower() != "deal status"]

    # Normalize text columns if present
    text_cols = ["name", "owner_code", "client_code", "deal_status", "deal_stage", "product", "sector"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_text)

    # Normalize numeric columns if present
    num_cols = ["deal_value", "closure_probability"]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(coerce_number)

    # Normalize date columns if present
    date_cols = ["close_date", "tentative_close_date", "created_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_date_flexible)

    return df


def normalize_work_orders(raw_work_orders: list) -> pd.DataFrame:
    """
    Translates, normalizes, and filters Work Order records.
    """
    mapped = map_columns(raw_work_orders, WORK_ORDERS_SCHEMA)
    df = pd.DataFrame(mapped)

    if df.empty:
        return pd.DataFrame(columns=[
            "item_id", "name", "deal_name", "customer_name_code", "nature_of_work",
            "last_executed_month", "execution_status", "data_delivery_date",
            "date_of_po", "document_type", "probable_start_date", "probable_end_date",
            "bd_kam_code", "sector", "type_of_work", "skylark_software_part",
            "last_invoice_date", "latest_invoice_no", "amount_excl_gst", "amount_incl_gst",
            "billed_excl_gst", "billed_incl_gst", "collected_incl_gst", "to_be_billed_excl_gst",
            "to_be_billed_incl_gst", "amount_receivable", "ar_priority_account",
            "quantity_by_ops", "quantities_per_po", "quantity_billed", "balance_quantity",
            "invoice_status", "expected_billing_month", "actual_billing_month",
            "actual_collection_month", "wo_status_billed", "collection_status",
            "collection_date", "billing_status"
        ])

    # Text columns
    text_cols = [
        "name", "deal_name", "customer_name_code", "nature_of_work",
        "execution_status", "sector", "billing_status", "document_type",
        "bd_kam_code", "type_of_work", "invoice_status", "collection_status"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_text)

    # Date columns
    date_cols = [
        "data_delivery_date", "date_of_po", "probable_start_date",
        "probable_end_date", "last_invoice_date", "collection_date"
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_date_flexible)

    # Numeric columns
    num_cols = [
        "amount_excl_gst", "amount_incl_gst", "billed_excl_gst",
        "billed_incl_gst", "collected_incl_gst", "to_be_billed_excl_gst",
        "to_be_billed_incl_gst", "amount_receivable", "quantity_by_ops",
        "quantities_per_po", "quantity_billed", "balance_quantity"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(coerce_number)

    return df