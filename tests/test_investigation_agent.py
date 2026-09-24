from datetime import datetime
from src.agent.investigator import FraudInvestigatorAgent
from src.agent.models import Transaction, TriggerEvent, TriggerType, ActionType


def test_agent_investigate_high_risk_device_ring():
    agent = FraudInvestigatorAgent()
    txn = Transaction(
        txn_id="TXN_TEST_RING",
        amount=1200.0,
        timestamp=datetime.utcnow(),
        model_risk_score=0.92,
        customer_id="CUST_RING_99",
        card_id="CARD_RING_99",
        merchant_id="MERCH_CRYPTO",
        device_id="DEV_RING_01",
        ip_address="198.51.100.42",
    )
    trigger = TriggerEvent(
        trigger_id="TRIG_RING_01",
        trigger_type=TriggerType.RISK_SCORE,
        transaction=txn,
    )

    ans = agent.investigate(trigger, case_id="CASE_TEST_RING")
    assert ans.case_id == "CASE_TEST_RING"
    assert ans.nba_pre_evidence.action == ActionType.BLOCK_CARD
    assert ans.graph_persistence_confirmed is True
    assert ans.sar_report is not None


def test_agent_investigate_uncertainty_and_customer_clear():
    agent = FraudInvestigatorAgent()
    agent.evidence_service.set_simulation_scenario("USER_CONFIRMED")

    txn = Transaction(
        txn_id="TXN_TEST_LEGIT",
        amount=250.0,
        timestamp=datetime.utcnow(),
        model_risk_score=0.62,
        customer_id="CUST_LEGIT_01",
        card_id="CARD_LEGIT_01",
        merchant_id="MERCH_HOTEL",
    )
    trigger = TriggerEvent(
        trigger_id="TRIG_LEGIT_01",
        trigger_type=TriggerType.RISK_SCORE,
        transaction=txn,
    )

    ans = agent.investigate(trigger, case_id="CASE_TEST_LEGIT")
    # Pre-evidence action was to ask confirmation
    assert ans.nba_pre_evidence.action == ActionType.REQUEST_CUSTOMER_CONFIRMATION
    # Post-evidence action allowed the transaction after customer cleared
    assert ans.nba_post_evidence.action == ActionType.ALLOW_TRANSACTION
    assert ans.received_evidence.customer_confirmed_legitimate is True
