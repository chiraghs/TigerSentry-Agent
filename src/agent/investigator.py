"""
Core Agentic Fraud Investigator
Orchestrates the 8-step investigation lifecycle, uncertainty assessment,
two-stage next-best actions (pre and post evidence), and TigerGraph persistence.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.agent.models import (
    TriggerEvent,
    GraphEvidence,
    NextBestAction,
    ActionType,
    ApprovalRoute,
    ControlledEvidenceRequest,
    ControlledEvidenceResponse,
    InvestigationAnswerFile,
    FraudPatternType,
)
from src.agent.state import InvestigationState
from src.tigergraph.client import TigerGraphClient
from src.tigergraph.mcp_server import TigerGraphMCPServer
from src.actions.mock_services import MockEvidenceService, MockActionExecutionService
from src.rag.policy_engine import PolicyEngine

logger = logging.getLogger("FraudInvestigator")


class FraudInvestigatorAgent:
    """Autonomous agent investigating fraud cases using TigerGraph, GraphRAG, and uncertainty reasoning."""

    def __init__(
        self,
        tg_client: Optional[TigerGraphClient] = None,
        evidence_service: Optional[MockEvidenceService] = None,
        action_service: Optional[MockActionExecutionService] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self.tg_client = tg_client or TigerGraphClient()
        self.mcp = TigerGraphMCPServer(self.tg_client)
        self.evidence_service = evidence_service or MockEvidenceService()
        self.action_service = action_service or MockActionExecutionService()
        self.policy_engine = policy_engine or PolicyEngine()

    def investigate(self, trigger: TriggerEvent, case_id: Optional[str] = None) -> InvestigationAnswerFile:
        """Runs the complete 8-step investigation lifecycle for a trigger event."""
        cid = case_id or f"CASE_{trigger.transaction.txn_id}_{int(datetime.utcnow().timestamp())}"
        state = InvestigationState(case_id=cid, trigger=trigger)
        state.log(f"Initiated investigation for txn {trigger.transaction.txn_id} triggered by {trigger.trigger_type}")

        # Step 1 & 2: Investigate Entities & Graph Traversal via MCP
        state.current_step = 2
        txn = trigger.transaction
        ring_res = self.mcp.execute_tool(
            "tg_detect_device_ring",
            {"device_id": txn.device_id, "ip_address": txn.ip_address},
        )
        velocity_res = self.mcp.execute_tool(
            "tg_detect_velocity_burst",
            {"card_id": txn.card_id, "minutes": 60},
        )
        travel_res = self.mcp.execute_tool(
            "tg_detect_impossible_travel",
            {"customer_id": txn.customer_id, "country": txn.country or "US"},
        )
        subgraph = self.mcp.execute_tool("tg_get_subgraph", {"txn_id": txn.txn_id})
        similar_cases_res = self.mcp.execute_tool("tg_get_similar_cases", {"txn_id": txn.txn_id, "top_k": 3})
        state.historical_cases = similar_cases_res.get("similar_cases", [])

        # Step 3: Gather Evidence & GraphRAG Policy Grounding
        state.current_step = 3
        state.graph_evidence = GraphEvidence(
            shared_device_card_count=ring_res.get("shared_cards_count", 1),
            shared_device_customer_count=ring_res.get("shared_customers_count", 1),
            shared_ip_customer_count=ring_res.get("shared_customers_count", 1),
            velocity_1h_txn_count=velocity_res.get("velocity_count", 1),
            velocity_1h_amount=velocity_res.get("velocity_amount", txn.amount),
            impossible_travel_detected=travel_res.get("impossible_travel_detected", False),
            travel_speed_kmh=travel_res.get("speed_kmh"),
            raw_subgraph_nodes=subgraph.get("nodes_count", 1),
            raw_subgraph_edges=subgraph.get("edges_count", 1),
        )

        state.identified_patterns = self.policy_engine.evaluate_graph_patterns(state.graph_evidence, txn)
        state.policy_matches = self.policy_engine.evaluate_policy_matches(state.identified_patterns, txn, state.graph_evidence)
        state.log(f"Identified patterns: {[p.value for p in state.identified_patterns]}")

        # Step 4: Assess Uncertainty
        state.current_step = 4
        self._assess_uncertainty(state)
        state.log(f"Risk Score: {state.risk_score:.2f}, Confidence: {state.confidence_score:.2f}, Uncertainty: {state.uncertainty_score:.2f}")

        # Step 5: Formulate Pre-Evidence Next-Best Action (Mandatory Hackathon Output)
        state.current_step = 5
        state.nba_pre_evidence = self._formulate_pre_evidence_nba(state)
        state.log(f"Pre-evidence NBA: {state.nba_pre_evidence.action.value} via route {state.nba_pre_evidence.approval_route.value}")

        # Step 6: Gather Additional Evidence when Needed (Controlled Policy Actions)
        state.current_step = 6
        needs_evidence = (
            not state.enough_evidence_to_act
            or state.nba_pre_evidence.action in [
                ActionType.REQUEST_CUSTOMER_CONFIRMATION,
                ActionType.REQUEST_STEP_UP_AUTH,
                ActionType.ESCALATE_TO_ANALYST,
            ]
        )

        if needs_evidence and state.risk_score < 0.90:
            self._request_controlled_evidence(state)
        else:
            state.log("High certainty or severe hard-risk threshold met; proceeding directly without delaying for interactive evidence.")

        # Step 7: Formulate Post-Evidence Next-Best Action & Compliance Review
        state.current_step = 7
        state.nba_post_evidence = self._formulate_post_evidence_nba(state)
        state.log(f"Post-evidence NBA: {state.nba_post_evidence.action.value} via route {state.nba_post_evidence.approval_route.value}")

        # Check SAR requirement
        sar_needed, sar_doc = self.policy_engine.generate_sar_if_warranted(
            state.case_id, txn, state.graph_evidence, state.identified_patterns
        )
        if sar_needed:
            state.sar_report = sar_doc
            state.log(f"Mandatory SAR generated: {sar_doc.sar_id}")

        # Step 8: Update Case Memory & Write to TigerGraph
        state.current_step = 8
        self._persist_case_memory(state)
        self._generate_explanations(state)

        return self._build_answer_file(state)

    def _assess_uncertainty(self, state: InvestigationState):
        """Calculates risk, confidence, and remaining uncertainty."""
        txn = state.trigger.transaction
        ev = state.graph_evidence

        # Base risk from model + graph boosts
        risk = txn.model_risk_score
        if FraudPatternType.DEVICE_IDENTITY_RING in state.identified_patterns:
            risk = max(risk, 0.92)
        if ev.impossible_travel_detected:
            risk = max(risk, 0.88)
        if ev.velocity_1h_txn_count >= 5:
            risk = max(risk, 0.82)

        state.risk_score = round(risk, 3)

        # Confidence is high if we have definitive graph proof or hard ring structures
        has_hard_pattern = any(
            p in state.identified_patterns
            for p in [FraudPatternType.DEVICE_IDENTITY_RING, FraudPatternType.IMPOSSIBLE_TRAVEL]
        )
        if ev.shared_device_card_count >= 3 or has_hard_pattern:
            state.confidence_score = 0.90
        elif 0.35 <= txn.model_risk_score <= 0.80:
            state.confidence_score = 0.50
        else:
            state.confidence_score = 0.80

        state.uncertainty_score = round(1.0 - state.confidence_score, 3)
        state.enough_evidence_to_act = state.uncertainty_score <= 0.20 or state.risk_score >= 0.90

    def _formulate_pre_evidence_nba(self, state: InvestigationState) -> NextBestAction:
        """Determines the recommended action and approval route BEFORE any additional evidence is collected."""
        if state.risk_score >= 0.90:
            return NextBestAction(
                action=ActionType.BLOCK_CARD,
                approval_route=ApprovalRoute.AUTOMATED,
                confidence=state.confidence_score,
                rationale="Critical risk score >= 0.90 and active syndicate ring indicators warrant immediate card block.",
                policy_citation="Bank Policy POL-101",
            )
        elif state.risk_score >= 0.60:
            return NextBestAction(
                action=ActionType.REQUEST_CUSTOMER_CONFIRMATION,
                approval_route=ApprovalRoute.AUTOMATED,
                confidence=state.confidence_score,
                rationale="Moderate-to-high risk with uncertainty. Recommend real-time customer validation challenge before hard account action.",
                policy_citation="Bank Policy POL-102",
            )
        elif state.risk_score >= 0.40:
            return NextBestAction(
                action=ActionType.MONITOR_ACCOUNT,
                approval_route=ApprovalRoute.AUTOMATED,
                confidence=state.confidence_score,
                rationale="Borderline risk score; recommend placing customer card on elevated 24-hour velocity monitoring.",
                policy_citation="Bank Policy POL-102",
            )
        else:
            return NextBestAction(
                action=ActionType.ALLOW_TRANSACTION,
                approval_route=ApprovalRoute.AUTOMATED,
                confidence=state.confidence_score,
                rationale="Low risk signals; normal user transaction profile confirmed.",
                policy_citation="Standard Transaction Policy",
            )

    def _request_controlled_evidence(self, state: InvestigationState):
        """Executes targeted, policy-approved evidence gathering action."""
        txn = state.trigger.transaction
        req = ControlledEvidenceRequest(
            evidence_type="CUSTOMER_SMS_VALIDATION",
            target_entity=txn.customer_id,
            request_details={"amount": txn.amount, "merchant": txn.merchant_id, "card_id": txn.card_id},
        )
        state.requested_evidence = req
        state.log(f"Dispatched controlled evidence request: {req.evidence_type} to customer {txn.customer_id}")

        resp = self.evidence_service.request_customer_validation(txn.customer_id, txn.txn_id, txn.amount)
        state.received_evidence = resp
        state.log(f"Received evidence response: status={resp.status}, legit={resp.customer_confirmed_legitimate}")

    def _formulate_post_evidence_nba(self, state: InvestigationState) -> NextBestAction:
        """Determines the updated action and required approval route AFTER evidence is received."""
        # If no additional evidence was requested, NBA remains as determined
        if not state.received_evidence:
            return state.nba_pre_evidence

        resp = state.received_evidence

        # Case 1: Customer confirmed they did NOT authorize transaction
        if resp.customer_confirmed_legitimate is False:
            route = ApprovalRoute.L1_FRAUD_ANALYST if state.trigger.transaction.amount < 5000 else ApprovalRoute.L2_RISK_MANAGER
            return NextBestAction(
                action=ActionType.FREEZE_ACCOUNT,
                approval_route=route,
                confidence=0.98,
                rationale="Customer explicitly confirmed unauthorized activity via two-factor SMS validation. Hard containment and investigation escalation initiated.",
                policy_citation="Bank Policy POL-101 / POL-103",
            )

        # Case 2: Customer confirmed transaction WAS legitimate
        elif resp.customer_confirmed_legitimate is True:
            return NextBestAction(
                action=ActionType.ALLOW_TRANSACTION,
                approval_route=ApprovalRoute.AUTOMATED,
                confidence=0.95,
                rationale="Customer verified charge legitimacy via registered device; uncertainty resolved, clearing false positive flag.",
                policy_citation="Bank Policy POL-102 (Customer Self-Service Clear)",
            )

        # Case 3: Customer timed out
        else:
            return NextBestAction(
                action=ActionType.BLOCK_CARD,
                approval_route=ApprovalRoute.L1_FRAUD_ANALYST,
                confidence=0.80,
                rationale="Customer verification challenge timed out. Precautionary temporary card block applied pending inbound analyst call.",
                policy_citation="Bank Policy POL-101 (Precautionary Hold)",
            )

    def _persist_case_memory(self, state: InvestigationState):
        """Persists the complete case to TigerGraph knowledge graph."""
        case_payload = {
            "status": "CLOSED" if state.nba_post_evidence.action in [ActionType.ALLOW_TRANSACTION, ActionType.CLOSE_CASE] else "UNDER_REVIEW",
            "fraud_type": state.identified_patterns[0].value if state.identified_patterns else "UNKNOWN",
            "risk_score": state.risk_score,
            "uncertainty": state.uncertainty_score,
            "recommended_action": state.nba_post_evidence.action.value,
            "approval_route": state.nba_post_evidence.approval_route.value,
            "sar_filed": state.sar_report is not None,
        }
        success = self.tg_client.write_investigation_case(state.case_id, case_payload)
        state.graph_persisted = success

    def _generate_explanations(self, state: InvestigationState):
        """Generates clear, defensible executive summaries and reasoning justifications."""
        txn = state.trigger.transaction
        ev = state.graph_evidence
        patterns = [p.value for p in state.identified_patterns]

        state.executive_summary = (
            f"Investigation {state.case_id} concluded with recommended action '{state.nba_post_evidence.action.value}' "
            f"routed through '{state.nba_post_evidence.approval_route.value}'. Initial risk assessment was {state.risk_score:.2f} "
            f"with uncertainty {state.uncertainty_score:.2f}. Identified typologies: {', '.join(patterns) if patterns else 'None'}."
        )

        state.reasoning_explanation = (
            f"EVIDENCE EVALUATED:\n"
            f"- Transaction: ${txn.amount:.2f} on card {txn.card_id} at merchant {txn.merchant_id}.\n"
            f"- TigerGraph Graph Evidence: {ev.shared_device_card_count} cards linked to device {txn.device_id or 'N/A'}, "
            f"1-hour velocity of {ev.velocity_1h_txn_count} txns totaling ${ev.velocity_1h_amount:.2f}.\n"
            f"- Impossible Travel: {ev.impossible_travel_detected}.\n"
            f"WHY ADDITIONAL EVIDENCE WAS REQUESTED:\n"
            f"Initial signals were ambiguous (uncertainty score {state.uncertainty_score:.2f}). To avoid unnecessary customer friction "
            f"and verify cardholder presence, a controlled SMS validation request was triggered under Policy POL-102.\n"
            f"DECISION JUSTIFICATION:\n"
            f"{state.nba_post_evidence.rationale} Policy compliance citation: {state.nba_post_evidence.policy_citation}."
        )

    def _build_answer_file(self, state: InvestigationState) -> InvestigationAnswerFile:
        """Converts state to the exact hackathon submission answer format."""
        return InvestigationAnswerFile(
            case_id=state.case_id,
            trigger=state.trigger,
            investigation_record={
                "steps_taken": state.investigation_log,
                "created_at": state.created_at.isoformat(),
                "policy_matches": [m.model_dump() for m in state.policy_matches],
                "historical_cases_referenced": state.historical_cases,
            },
            graph_evidence=state.graph_evidence,
            identified_patterns=state.identified_patterns,
            uncertainty_level=state.uncertainty_score,
            nba_pre_evidence=state.nba_pre_evidence,
            requested_evidence=state.requested_evidence,
            received_evidence=state.received_evidence,
            nba_post_evidence=state.nba_post_evidence,
            sar_report=state.sar_report,
            graph_persistence_confirmed=state.graph_persisted,
            executive_summary=state.executive_summary,
            reasoning_explanation=state.reasoning_explanation,
        )
