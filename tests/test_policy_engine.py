from datetime import datetime
from src.rag.policy_engine import PolicyEngine
from src.agent.models import Transaction, GraphEvidence, FraudPatternType


def test_policy_engine_detection():
    engine = PolicyEngine()
    
    txn = Transaction(
        txn_id="TXN_TEST_1",
        amount=6200.0,
        timestamp=datetime.utcnow(),
        model_risk_score=0.91,
        customer_id="CUST_1",
        card_id="CARD_1",
        merchant_id="MERCH_1",
    )
    
    evidence = GraphEvidence(
        shared_device_card_count=4,
        shared_device_customer_count=3,
        velocity_1h_txn_count=7,
        velocity_1h_amount=7500.0,
        impossible_travel_detected=False,
    )

    patterns = engine.evaluate_graph_patterns(evidence, txn)
    assert FraudPatternType.DEVICE_IDENTITY_RING in patterns
    assert FraudPatternType.CARD_TESTING_VELOCITY in patterns

    sar_needed, sar_doc = engine.generate_sar_if_warranted("CASE_99", txn, evidence, patterns)
    assert sar_needed is True
    assert sar_doc is not None
    assert sar_doc.total_suspicious_amount >= 5000.0
