import pandas as pd
import re
from .schema import map_columns, DEALS_SCHEMA, WORK_ORDERS_SCHEMA

def parse_date_flexible(val):
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

def normalize_text(val):
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

    # Map sector spelling variations
    val_lower = val_str.lower()
    if val_lower in ("power", "powerline", "power lines"):
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

def coerce_number(val):
    """
    Strips currency symbols, commas, spaces and converts value to float.
    """
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null", "nat", "masked deal value", "amount"):
        return 0.0
    
    # Retain digits, decimals, and negative signs
    clean_str = re.sub(r'[^\d\.\-]', '', val_str)
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def normalize_deals(raw_deals: list) -> pd.DataFrame:
    """
    Translates, normalizes, and filters Deals records.
    Filters out repeated header rows.
    """
    mapped = map_columns(raw_deals, DEALS_SCHEMA)
    df = pd.DataFrame(mapped)

    if df.empty:
        return pd.DataFrame(columns=[
            "item_id", "name", "owner_code", "client_code", "deal_status",
            "close_date", "closure_probability", "deal_value",
            "tentative_close_date", "deal_stage", "product", "sector", "created_date"
        ])

    # Filter out repeated header rows leak
    df = df[df["name"].astype(str).str.lower() != "deal name"]
    df = df[df["sector"].astype(str).str.lower() != "sector/service"]
    df = df[df["deal_status"].astype(str).str.lower() != "deal status"]

    # Normalize fields
    df["name"] = df["name"].apply(normalize_text)
    df["owner_code"] = df["owner_code"].apply(normalize_text)
    df["client_code"] = df["client_code"].apply(normalize_text)
    df["deal_status"] = df["deal_status"].apply(normalize_text)
    df["deal_stage"] = df["deal_stage"].apply(normalize_text)
    df["product"] = df["product"].apply(normalize_text)
    df["sector"] = df["sector"].apply(normalize_text)

    df["deal_value"] = df["deal_value"].apply(coerce_number)
    df["closure_probability"] = df["closure_probability"].apply(coerce_number)

    df["close_date"] = df["close_date"].apply(parse_date_flexible)
    df["tentative_close_date"] = df["tentative_close_date"].apply(parse_date_flexible)
    df["created_date"] = df["created_date"].apply(parse_date_flexible)

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

    # Basic text cleanup
    df["name"] = df["name"].apply(normalize_text)
    df["deal_name"] = df["deal_name"].apply(normalize_text)
    df["customer_name_code"] = df["customer_name_code"].apply(normalize_text)
    df["nature_of_work"] = df["nature_of_work"].apply(normalize_text)
    df["execution_status"] = df["execution_status"].apply(normalize_text)
    df["sector"] = df["sector"].apply(normalize_text)
    df["billing_status"] = df["billing_status"].apply(normalize_text)

    # Date normalization
    df["data_delivery_date"] = df["data_delivery_date"].apply(parse_date_flexible)
    df["date_of_po"] = df["date_of_po"].apply(parse_date_flexible)
    df["probable_start_date"] = df["probable_start_date"].apply(parse_date_flexible)
    df["probable_end_date"] = df["probable_end_date"].apply(parse_date_flexible)
    df["last_invoice_date"] = df["last_invoice_date"].apply(parse_date_flexible)

    # Coerce numeric values
    df["amount_excl_gst"] = df["amount_excl_gst"].apply(coerce_number)
    df["amount_incl_gst"] = df["amount_incl_gst"].apply(coerce_number)
    df["billed_excl_gst"] = df["billed_excl_gst"].apply(coerce_number)
    df["billed_incl_gst"] = df["billed_incl_gst"].apply(coerce_number)
    df["collected_incl_gst"] = df["collected_incl_gst"].apply(coerce_number)
    df["to_be_billed_excl_gst"] = df["to_be_billed_excl_gst"].apply(coerce_number)
    df["to_be_billed_incl_gst"] = df["to_be_billed_incl_gst"].apply(coerce_number)
    df["amount_receivable"] = df["amount_receivable"].apply(coerce_number)

    return df
