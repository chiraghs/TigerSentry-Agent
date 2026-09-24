"""
Tests for downstream mock banking API actions via ActionDispatcher.
"""

from src.agent.action_dispatcher import ActionDispatcher


def test_action_dispatcher_block_card():
    res = ActionDispatcher.execute_action("BLOCK_CARD", "HHG-001", {"card_id": "CARD-TEST-01"})
    assert res["status"] == "EXECUTED"
    assert res["http_status"] == 200
    assert "CMS" in res["system"]


def test_action_dispatcher_freeze_account():
    res = ActionDispatcher.execute_action("FREEZE_ACCOUNT", "HHG-001", {"customer_id": "CUST-TEST-01"})
    assert res["status"] == "EXECUTED"
    assert res["http_status"] == 200
    assert "Deposit Core" in res["system"]


def test_action_dispatcher_file_report():
    res = ActionDispatcher.execute_action("FILE_REPORT", "HHG-001", {"exposure_usd": 1500.0})
    assert res["status"] == "SUBMITTED"
    assert res["http_status"] in (200, 201)
    assert "FinCEN" in res["system"]


def test_action_dispatcher_execute_all():
    actions = ["BLOCK_CARD", "CREATE_CASE", "FILE_REPORT"]
    results = ActionDispatcher.execute_all(actions, "HHG-001")
    assert len(results) == 3
    assert all(r["http_status"] in (200, 201) for r in results)
