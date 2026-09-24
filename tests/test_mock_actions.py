import pytest
from src.actions.mock_services import MockEvidenceService, MockActionExecutionService
from src.agent.models import SARReport


def test_mock_evidence_service():
    service = MockEvidenceService()
    
    # Test user confirmed
    service.set_simulation_scenario("USER_CONFIRMED")
    resp = service.request_customer_validation("cust_legit", "txn_101", 150.0)
    assert resp.customer_confirmed_legitimate is True

    # Test user fraud alert
    service.set_simulation_scenario("USER_FRAUD_ALERT")
    resp_fraud = service.request_customer_validation("cust_fraud", "txn_102", 1500.0)
    assert resp_fraud.customer_confirmed_legitimate is False

    # Test step up auth failure
    service.set_simulation_scenario("MFA_FAILED")
    resp_mfa = service.request_step_up_auth("cust_mfa")
    assert resp_mfa.mfa_passed is False


def test_mock_action_execution():
    actions = MockActionExecutionService()
    res = actions.block_card("CARD_999", "Velocity breach", "AUTO_POLICY")
    assert res["status"] == "EXECUTED"
    assert len(actions.action_history) == 1
