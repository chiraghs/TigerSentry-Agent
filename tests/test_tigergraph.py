import pytest
from src.tigergraph.client import TigerGraphClient
from src.tigergraph.mcp_server import TigerGraphMCPServer


def test_tigergraph_client_queries():
    client = TigerGraphClient(mode="mock")
    
    # Test device ring query
    res_ring = client.detect_device_ring("device_ring_01", "198.51.100.42")
    assert res_ring["shared_cards_count"] >= 3
    assert res_ring["is_ring_detected"] is True

    # Test velocity burst
    res_vel = client.detect_velocity_burst("card_burst_01")
    assert res_vel["velocity_count"] >= 5

    # Test impossible travel
    from datetime import datetime
    res_travel = client.detect_impossible_travel("cust_travel_01", "SG", datetime.utcnow())
    assert res_travel["impossible_travel_detected"] is True

    # Test case memory query
    similar = client.get_similar_cases("TXN_123", top_k=2)
    assert len(similar) == 2
    assert "outcome" in similar[0]


def test_tigergraph_mcp_server():
    mcp = TigerGraphMCPServer()
    tools = mcp.get_available_tools()
    tool_names = [t["name"] for t in tools]
    assert "tg_detect_device_ring" in tool_names
    assert "tg_detect_velocity_burst" in tool_names

    res = mcp.execute_tool("tg_detect_device_ring", {"device_id": "ring_test", "ip_address": "198.51.1.1"})
    assert "shared_cards_count" in res
