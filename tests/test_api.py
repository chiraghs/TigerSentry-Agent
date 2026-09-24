"""
Integration tests for FastAPI endpoints in src.api.server.
"""

from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "partner" in data
    assert data["partner"] == "TigerGraph"
    assert "llm_provider" in data


def test_list_and_get_cases():
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    case_ids = response.json()
    assert isinstance(case_ids, list)
    assert len(case_ids) > 0
    
    first_case = case_ids[0]
    case_resp = client.get(f"/api/v1/cases/{first_case}")
    assert case_resp.status_code == 200
    case_data = case_resp.json()
    assert case_data["case_id"] == first_case
    assert "case" in case_data
    assert "next_best_actions" in case_data
    assert "sar" in case_data


def test_analytics_endpoint():
    response = client.get("/api/v1/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert data["kpis"]["total_cases"] == 20
    assert "crm_cases" in data
    assert len(data["crm_cases"]) == 20


def test_transaction_ledger_endpoint():
    response = client.get("/api/v1/transactions/ledger?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["transactions"]) == 10


def test_llm_status_and_chat_endpoints():
    status_resp = client.get("/api/v1/llm/status")
    assert status_resp.status_code == 200
    assert "provider" in status_resp.json()

    chat_resp = client.post("/api/v1/agent/chat", json={
        "case_id": "HHG-001",
        "question": "What is the verdict for this case?"
    })
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "response" in chat_data
