import pytest
import pandas as pd
from agent.tools import query_deals, query_work_orders, join_boards, aggregate_metrics

@pytest.fixture
def sample_deals():
    return pd.DataFrame([
        {"item_id": "d1", "name": "Deal 1", "status": "Won", "value": 100.0, "close_date": "2026-08-10", "account_name": "Acme"},
        {"item_id": "d2", "name": "Deal 2", "status": "Proposal", "value": 50.0, "close_date": "2026-08-12", "account_name": "Globex"}
    ])

@pytest.fixture
def sample_work_orders():
    return pd.DataFrame([
        {"item_id": "w1", "name": "WO 1", "status": "In Progress", "priority": "High", "due_date": "2026-09-01", "deal_name": "Deal 1"},
        {"item_id": "w2", "name": "WO 2", "status": "Pending", "priority": "Medium", "due_date": "2026-09-05", "deal_name": "Deal 2"}
    ])

def test_query_deals(sample_deals):
    res = query_deals(sample_deals)
    assert len(res) == 2
    assert "value" in res.columns

def test_query_work_orders(sample_work_orders):
    res = query_work_orders(sample_work_orders)
    assert len(res) == 2
    assert "priority" in res.columns

def test_join_boards(sample_deals, sample_work_orders):
    res = join_boards(sample_deals, sample_work_orders)
    assert len(res) == 2
    # Columns from both sides should exist
    assert "value" in res.columns
    assert "priority" in res.columns
    assert "name_deal" in res.columns
    assert "name_wo" in res.columns

def test_aggregate_metrics(sample_deals, sample_work_orders):
    # Sum of value grouped by status on deals
    agg = aggregate_metrics(sample_deals, sample_work_orders, "deals", "status", "value", "sum")
    assert len(agg) == 2
    assert "sum_of_value" in agg.columns
    
    # Verify values
    won_val = agg.loc[agg["status"] == "Won", "sum_of_value"].values[0]
    assert won_val == 100.0

def test_aggregate_invalid_column(sample_deals, sample_work_orders):
    with pytest.raises(ValueError):
        aggregate_metrics(sample_deals, sample_work_orders, "deals", "invalid_col", "value", "sum")
        
    with pytest.raises(ValueError):
        aggregate_metrics(sample_deals, sample_work_orders, "deals", "status", "value", "invalid_func")
