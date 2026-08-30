import pytest
import pandas as pd
from data_processing.schema import map_columns, DEALS_SCHEMA, WORK_ORDERS_SCHEMA
from data_processing.normalizer import normalize_deals, normalize_work_orders

def test_map_columns():
    raw_items = [
        {"id": "1", "name": "Item 1", "deal_status": "Won", "deal_value": "100"},
        {"id": "2", "name": "Item 2", "deal_status": "Qualified", "deal_value": "200"}
    ]
    
    mapped = map_columns(raw_items, DEALS_SCHEMA)
    
    assert len(mapped) == 2
    assert mapped[0]["item_id"] == "1"
    assert mapped[0]["name"] == "Item 1"
    assert mapped[0]["status"] == "Won"
    assert mapped[0]["value"] == "100"
    assert "deal_status" not in mapped[0]

def test_normalize_deals():
    raw_deals = [
        {"id": "1", "name": "  Deal A  ", "deal_status": " Won ", "deal_value": "150000.50", "close_date": "2026-08-30", "account_name": "Acme"},
        {"id": "2", "name": "Deal B", "deal_status": "", "deal_value": "abc", "close_date": "", "account_name": ""}
    ]
    
    df = normalize_deals(raw_deals)
    
    assert len(df) == 2
    assert df.loc[0, "name"] == "Deal A"
    assert df.loc[0, "status"] == "Won"
    assert df.loc[0, "value"] == 150000.50
    assert df.loc[0, "close_date"] == pd.Timestamp("2026-08-30")
    
    # Check nulls/invalid defaults
    assert df.loc[1, "status"] == "None"
    assert df.loc[1, "value"] == 0.0
    assert pd.isna(df.loc[1, "close_date"])
    assert df.loc[1, "account_name"] == "None"

def test_normalize_work_orders():
    raw_wo = [
        {"id": "w1", "name": "WO 1", "wo_status": "Completed", "wo_priority": "High", "due_date": "2026-09-01", "deal_link": "Acme Deal"}
    ]
    
    df = normalize_work_orders(raw_wo)
    
    assert len(df) == 1
    assert df.loc[0, "status"] == "Completed"
    assert df.loc[0, "priority"] == "High"
    assert df.loc[0, "deal_name"] == "Acme Deal"
    assert df.loc[0, "due_date"] == pd.Timestamp("2026-09-01")

def test_normalize_empty():
    deals_df = normalize_deals([])
    assert isinstance(deals_df, pd.DataFrame)
    assert "value" in deals_df.columns
    
    wo_df = normalize_work_orders([])
    assert isinstance(wo_df, pd.DataFrame)
    assert "priority" in wo_df.columns
