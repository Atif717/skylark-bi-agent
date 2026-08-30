import pytest
from unittest.mock import MagicMock, patch
from monday_client.client import MondayClient
from monday_client.fetch import get_deals, get_work_orders

def test_mock_client_direct_query():
    client = MondayClient(api_token="mock_token")
    # Query deals
    deals_data = client.execute_query("query { deals }")
    assert "data" in deals_data
    assert "boards" in deals_data["data"]
    assert deals_data["data"]["boards"][0]["id"] == "1234567890"

    # Query work orders
    wo_data = client.execute_query("query { work_orders }")
    assert "data" in wo_data
    assert "boards" in wo_data["data"]
    assert wo_data["data"]["boards"][0]["id"] == "0987654321"

def test_fetch_get_deals():
    client = MondayClient(api_token="mock_token")
    deals = get_deals(client, "1234567890")
    
    assert len(deals) > 0
    # Deals should be flat parsed
    assert "id" in deals[0]
    assert "name" in deals[0]
    assert "deal_status" in deals[0]
    assert "deal_value" in deals[0]

def test_fetch_get_work_orders():
    client = MondayClient(api_token="mock_token")
    work_orders = get_work_orders(client, "0987654321")
    
    assert len(work_orders) > 0
    # Work orders should be flat parsed
    assert "id" in work_orders[0]
    assert "name" in work_orders[0]
    assert "wo_status" in work_orders[0]
    assert "deal_link" in work_orders[0]

import requests

@patch("requests.post")
def test_real_client_network_error(mock_post):
    # Simulate exception on HTTP request
    mock_post.side_effect = requests.RequestException("Connection timed out")
    
    client = MondayClient(api_token="real_token_123")
    with pytest.raises(RuntimeError) as exc_info:
        client.execute_query("{ boards { id } }")
        
    assert "Connection Error" in str(exc_info.value)
