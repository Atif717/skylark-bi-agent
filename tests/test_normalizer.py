import pytest
import pandas as pd
from data_processing.schema import map_columns, DEALS_SCHEMA, WORK_ORDERS_SCHEMA
from data_processing.normalizer import normalize_deals, normalize_work_orders, parse_date_flexible, coerce_number, normalize_text

def test_parse_date_flexible():
    assert parse_date_flexible("2026-08-30") == pd.Timestamp("2026-08-30")
    assert parse_date_flexible("2025-12-26 00:00:00") == pd.Timestamp("2025-12-26")
    assert pd.isna(parse_date_flexible("None"))
    assert pd.isna(parse_date_flexible(""))

def test_normalize_text():
    assert normalize_text("  powerlines ") == "Powerline"
    assert normalize_text("renewables") == "Renewables"
    assert normalize_text("construction") == "Construction"
    assert normalize_text("nan") == "None"

def test_coerce_number():
    assert coerce_number("$ 150,000.50 ") == 150000.50
    assert coerce_number("Rs. 45,000") == 45000.0
    assert coerce_number("abc") == 0.0

def test_map_columns():
    raw_items = [
        {"id": "d1", "name": "Naruto", "deal_status": "Won", "masked_deal_value": "120000"},
        {"id": "d2", "name": "Sasuke", "deal_status": "Proposal", "masked_deal_value": "45000"}
    ]
    
    mapped = map_columns(raw_items, DEALS_SCHEMA)
    assert len(mapped) == 2
    assert mapped[0]["item_id"] == "d1"
    assert mapped[0]["name"] == "Naruto"
    assert mapped[0]["deal_status"] == "Won"
    assert mapped[0]["deal_value"] == "120000"

def test_normalize_deals():
    raw_deals = [
        {"id": "d1", "name": "Naruto", "deal_status": "Won", "masked_deal_value": "$ 120,000", "close_date_a": "2026-08-15", "sector_service": "mining"},
        {"id": "d2", "name": "Deal Name", "deal_status": "Deal Status", "masked_deal_value": "", "close_date_a": "", "sector_service": "Sector/service"} # Header leak
    ]
    
    df = normalize_deals(raw_deals)
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Naruto"
    assert df.iloc[0]["deal_status"] == "Won"
    assert df.iloc[0]["deal_value"] == 120000.0
    assert df.iloc[0]["sector"] == "Mining"
    assert df.iloc[0]["close_date"] == pd.Timestamp("2026-08-15")

def test_normalize_work_orders():
    raw_wo = [
        {"id": "w1", "name": "WO_1", "deal_name_masked": "Scooby-Doo", "customer_name_code": "WOCOMPANY_002", "execution_status": "Completed", "amount_excl_gst": "12000"}
    ]
    df = normalize_work_orders(raw_wo)
    assert len(df) == 1
    assert df.iloc[0]["deal_name"] == "Scooby-Doo"
    assert df.iloc[0]["customer_name_code"] == "WOCOMPANY_002"
    assert df.iloc[0]["execution_status"] == "Completed"
    assert df.iloc[0]["amount_excl_gst"] == 12000.0
