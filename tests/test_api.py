from fastapi.testclient import TestClient
from datetime import datetime
from src.api.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "tigergraph_mode" in data


def test_investigate_endpoint():
    payload = {
        "trigger_id": "TRIG_API_01",
        "trigger_type": "RISK_SCORE",
        "transaction": {
            "txn_id": "TXN_API_101",
            "amount": 750.0,
            "timestamp": datetime.utcnow().isoformat(),
            "model_risk_score": 0.89,
            "customer_id": "CUST_API_01",
            "card_id": "CARD_API_01",
            "merchant_id": "MERCH_ELECTRONICS",
            "device_id": "DEV_EMULATOR_RING_99",
            "ip_address": "198.51.100.42",
            "country": "US",
            "city": "Dallas",
            "is_online": True,
            "attributes": {},
        },
        "source": "API Test Harness",
        "initial_notes": "Automated test trigger",
    }

    response = client.post("/api/v1/investigate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "case_id" in data
    assert "nba_pre_evidence" in data
    assert "nba_post_evidence" in data
    assert data["nba_pre_evidence"]["action"] == "BLOCK_CARD"
    assert data["graph_persistence_confirmed"] is True


def test_list_and_get_cases():
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    case_ids = response.json()
    assert isinstance(case_ids, list)
    if case_ids:
        sample_id = case_ids[0]
        case_resp = client.get(f"/api/v1/cases/{sample_id}")
        assert case_resp.status_code == 200
        case_data = case_resp.json()
        assert case_data["case_id"] == sample_id
