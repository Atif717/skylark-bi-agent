import pytest
import pandas as pd
from agent.tools import filter_deals, filter_work_orders, join_deals_and_orders, aggregate, generate_leadership_summary

@pytest.fixture
def sample_deals():
    return pd.DataFrame([
        {"item_id": "d1", "name": "Deal 1", "deal_status": "Won", "deal_value": 100.0, "close_date": pd.Timestamp("2026-08-10"), "sector": "Mining"},
        {"item_id": "d2", "name": "Deal 2", "deal_status": "Proposal", "deal_value": 50.0, "close_date": pd.Timestamp("2026-08-12"), "sector": "Powerline"}
    ])

@pytest.fixture
def sample_work_orders():
    return pd.DataFrame([
        {"item_id": "w1", "name": "WO_1", "execution_status": "Completed", "sector": "Mining", "deal_name": "Deal 1", "amount_excl_gst": 10000.0, "collected_incl_gst": 11800.0, "billed_excl_gst": 10000.0},
        {"item_id": "w2", "name": "WO_2", "execution_status": "Ongoing", "sector": "Powerline", "deal_name": "Deal 2", "amount_excl_gst": 5000.0, "collected_incl_gst": 0.0, "billed_excl_gst": 2000.0}
    ])

def test_filter_deals(sample_deals):
    res = filter_deals(sample_deals, quality_reports=[], sector="Mining")
    df = res["data"]
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Deal 1"

def test_filter_work_orders(sample_work_orders):
    res = filter_work_orders(sample_work_orders, quality_reports=[], status="Ongoing")
    df = res["data"]
    assert len(df) == 1
    assert df.iloc[0]["name"] == "WO_2"

def test_join_deals_and_orders(sample_deals, sample_work_orders):
    res = join_deals_and_orders(sample_deals, sample_work_orders, [], [])
    df = res["data"]
    assert len(df) == 2
    assert "deal_value" in df.columns
    assert "execution_status" in df.columns

def test_aggregate_deals(sample_deals):
    res = aggregate(sample_deals, [], "sector", "deal_value", "sum")
    df = res["data"]
    assert len(df) == 2
    # Verify values
    mining_val = df.loc[df["sector"] == "Mining", "sum_of_deal_value"].values[0]
    assert mining_val == 100.0

def test_generate_leadership_summary(sample_deals, sample_work_orders):
    res = generate_leadership_summary(sample_deals, sample_work_orders, [], [])
    stats = res["stats"]
    assert stats["total_deals_count"] == 2
    assert stats["total_work_orders"] == 2
    assert stats["work_order_completion_rate"] == "50.0% (1/2)"
    assert stats["revenue_billed_excl_gst"] == 12000.0
    assert stats["revenue_collected_incl_gst"] == 11800.0
