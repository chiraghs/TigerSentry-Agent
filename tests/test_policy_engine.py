"""
Tests for PolicyEngine evaluating rules R1 to R10, approval routing, and SAR synthesis.
"""

from src.rag.policy_engine import PolicyEngine
from src.agent.models import PolicyAction, ApprovalRoute, FraudPattern


def test_policy_engine_routing():
    engine = PolicyEngine()
    
    # Auto route actions
    assert engine.route_action(PolicyAction.ALLOW_TRANSACTION) == ApprovalRoute.AUTO
    assert engine.route_action(PolicyAction.VERIFY_WITH_CUSTOMER) == ApprovalRoute.AUTO
    assert engine.route_action(PolicyAction.CREATE_CASE) == ApprovalRoute.AUTO

    # Block card routing threshold ($2,500)
    assert engine.route_action(PolicyAction.BLOCK_CARD, exposure_usd=1200.0) == ApprovalRoute.L1
    assert engine.route_action(PolicyAction.BLOCK_CARD, exposure_usd=5000.0) == ApprovalRoute.L2

    # Senior manager actions
    assert engine.route_action(PolicyAction.FILE_REPORT) == ApprovalRoute.L2
    assert engine.route_action(PolicyAction.BLOCK_ALL_CARDS) == ApprovalRoute.L2


def test_policy_engine_initial_actions():
    engine = PolicyEngine()

    # R1: Single weak signal (< 0.70)
    actions = engine.evaluate_initial_actions(
        fraud_prob=0.62,
        pattern=FraudPattern.OUT_OF_REGION_USE,
        exposure_usd=150.0,
        is_single_signal=True
    )
    act_types = [a.action for a in actions]
    assert PolicyAction.VERIFY_WITH_CUSTOMER in act_types
    assert PolicyAction.MONITOR_CARD in act_types

    # High probability fraud (> 0.70)
    actions_high = engine.evaluate_initial_actions(
        fraud_prob=0.92,
        pattern=FraudPattern.CARD_NOT_PRESENT_NEW_DEVICE,
        exposure_usd=3000.0,
        is_single_signal=False
    )
    act_types_high = [a.action for a in actions_high]
    assert PolicyAction.BLOCK_CARD in act_types_high
    assert PolicyAction.FILE_REPORT in act_types_high


def test_policy_engine_sar_builder():
    engine = PolicyEngine()
    sar = engine.build_sar(
        should_file=True,
        reason="R2: confirmed unauthorized charge",
        case_id="HHG-001",
        customer_id="C12382",
        card_id="CARD-01",
        affected_txn_ids=["3514030"],
        connected_cards=["CARD-02"],
        connected_devices=["DEV-01"],
        exposure_usd=1250.0,
        activity_dates=["2016-12-01"],
        narrative_detail="Out of region transactions observed without prior travel notice.",
    )
    assert sar.file is True
    assert sar.total_amount_usd == 1250.0
    assert "C12382" in sar.subjects
    assert "CARD-01" in sar.subjects
    assert len(sar.narrative) > 50
