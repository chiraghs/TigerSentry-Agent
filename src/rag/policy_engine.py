"""
Official Fraud Policy & Regulatory Rules Engine
Implements rules R1 through R10 and approval routing from Fraud Policy v1.0.
"""

from typing import Dict, Any, List, Tuple, Optional
from src.agent.models import (
    PolicyAction,
    ApprovalRoute,
    ActionItem,
    FraudPattern,
    CaseVerdict,
    SAR,
)


class PolicyEngine:
    """Evaluates fraud cases against Bank Fraud Policy v1.0 and regulatory mandates."""

    def route_action(self, action: PolicyAction, exposure_usd: float = 0.0) -> ApprovalRoute:
        """Determines the required approval route according to Section 2 of Fraud Policy."""
        if action in [
            PolicyAction.ALLOW_TRANSACTION,
            PolicyAction.MONITOR_CARD,
            PolicyAction.MONITOR_CONNECTED_CARDS,
            PolicyAction.WARN_CUSTOMER,
            PolicyAction.VERIFY_WITH_CUSTOMER,
            PolicyAction.STEP_UP_AUTH,
            PolicyAction.GENERATE_REPORT,
            PolicyAction.CREATE_CASE,
            PolicyAction.ESCALATE_TO_ANALYST,
            PolicyAction.CLOSE_NO_FRAUD,
        ]:
            return ApprovalRoute.AUTO

        if action == PolicyAction.DECLINE_TRANSACTION:
            return ApprovalRoute.L1

        if action == PolicyAction.BLOCK_CARD:
            return ApprovalRoute.L1 if exposure_usd <= 2500.0 else ApprovalRoute.L2

        if action in [PolicyAction.BLOCK_ALL_CARDS, PolicyAction.FILE_REPORT]:
            return ApprovalRoute.L2

        return ApprovalRoute.AUTO

    def evaluate_initial_actions(
        self,
        fraud_prob: float,
        pattern: FraudPattern,
        exposure_usd: float,
        is_single_signal: bool,
        is_card_testing: bool = False,
    ) -> List[ActionItem]:
        """
        Determines the initial next-best actions before requesting additional evidence.
        """
        actions: List[ActionItem] = []

        # R5: Card testing sequence
        if is_card_testing or pattern == FraudPattern.CARD_TESTING:
            if exposure_usd > 100.0:
                route = self.route_action(PolicyAction.BLOCK_CARD, exposure_usd)
                actions.append(ActionItem(action=PolicyAction.BLOCK_CARD, route=route, reason="R5: testing sequence observed, purchase already cleared"))
            else:
                actions.append(ActionItem(action=PolicyAction.DECLINE_TRANSACTION, route=ApprovalRoute.L1, reason="R5: testing sequence observed"))
                actions.append(ActionItem(action=PolicyAction.STEP_UP_AUTH, route=ApprovalRoute.AUTO, reason="R5: step-up authentication challenge required"))
            actions.append(ActionItem(action=PolicyAction.CREATE_CASE, route=ApprovalRoute.AUTO, reason="R5: card testing requires internal case record"))
            return actions

        # R1: Weak signal (< 0.70) on a single signal -> verify before blocking
        if is_single_signal and fraud_prob < 0.70:
            actions.append(ActionItem(
                action=PolicyAction.VERIFY_WITH_CUSTOMER,
                route=ApprovalRoute.AUTO,
                reason="R1: probability below 0.70 on single signal, verify before blocking",
            ))
            if exposure_usd > 0:
                actions.append(ActionItem(
                    action=PolicyAction.MONITOR_CARD,
                    route=ApprovalRoute.AUTO,
                    reason="R1: card placed on 72h elevated monitoring pending verification",
                ))
            return actions

        # Strong signal (> 0.70)
        if fraud_prob >= 0.70:
            route = self.route_action(PolicyAction.BLOCK_CARD, exposure_usd)
            actions.append(ActionItem(action=PolicyAction.BLOCK_CARD, route=route, reason=f"Strong fraud indicators (prob {fraud_prob:.2f})"))
            actions.append(ActionItem(action=PolicyAction.CREATE_CASE, route=ApprovalRoute.AUTO, reason="Section 3a: case creation warranted for high probability fraud"))
            if exposure_usd > 1000.0 or pattern in [FraudPattern.CARD_NOT_PRESENT_NEW_DEVICE, FraudPattern.ACCOUNT_TAKEOVER]:
                actions.append(ActionItem(action=PolicyAction.FILE_REPORT, route=ApprovalRoute.L2, reason="Section 3a: confirmed/strong fraud with exposure > $1,000"))
            return actions

        # Default low risk
        actions.append(ActionItem(action=PolicyAction.ALLOW_TRANSACTION, route=ApprovalRoute.AUTO, reason="Low risk signal, activity within normal parameters"))
        return actions

    def evaluate_final_actions(
        self,
        initial_actions: List[ActionItem],
        assumed_response: str,
        fraud_prob: float,
        exposure_usd: float,
        has_shared_origin: bool = False,
        connected_cards: List[str] = None,
    ) -> Tuple[List[ActionItem], str]:
        """
        Determines the final next-best actions AFTER assumed evidence response.
        """
        connected_cards = connected_cards or []
        resp_lower = assumed_response.lower()

        # R3: Customer confirms transaction
        if "confirm" in resp_lower or "yes" in resp_lower or "authorized" in resp_lower:
            final_actions = [
                ActionItem(action=PolicyAction.ALLOW_TRANSACTION, route=ApprovalRoute.AUTO, reason="R3: customer confirmed transaction authenticity"),
                ActionItem(action=PolicyAction.CLOSE_NO_FRAUD, route=ApprovalRoute.AUTO, reason="R3: case closed as false alarm after cardholder verification"),
            ]
            change = "Customer confirmation cleared the alert; recommended actions updated to allow transaction and close case."
            return final_actions, change

        # R2: Customer denies transaction
        if "deni" in resp_lower or "not make" in resp_lower or "fraud" in resp_lower or "did not" in resp_lower:
            route = self.route_action(PolicyAction.BLOCK_CARD, exposure_usd)
            final_actions = [
                ActionItem(action=PolicyAction.BLOCK_CARD, route=route, reason=f"R2: customer denied transaction; exposure ${exposure_usd:.2f}"),
                ActionItem(action=PolicyAction.CREATE_CASE, route=ApprovalRoute.AUTO, reason="R2: case record opened in graph"),
            ]
            if exposure_usd > 1000.0 or has_shared_origin or len(connected_cards) > 0:
                final_actions.append(ActionItem(
                    action=PolicyAction.FILE_REPORT,
                    route=ApprovalRoute.L2,
                    reason="R2 and Section 3a: customer denied unauthorized use with exposure > $1,000 or shared origin",
                ))
            if has_shared_origin or len(connected_cards) > 0:
                final_actions.append(ActionItem(
                    action=PolicyAction.MONITOR_CONNECTED_CARDS,
                    route=ApprovalRoute.AUTO,
                    reason=f"R6: shared infrastructure links this case to {len(connected_cards)} other cards",
                ))
            change = f"Customer denial confirmed fraud (probability raised to {fraud_prob:.2f}), confirming card block and triggering case creation."
            return final_actions, change

        # R4: No reply / timeout
        if "timeout" in resp_lower or "no reply" in resp_lower:
            final_actions = [
                ActionItem(action=PolicyAction.DECLINE_TRANSACTION, route=ApprovalRoute.L1, reason="R4: pending authorization declined after no response within window"),
                ActionItem(action=PolicyAction.MONITOR_CARD, route=ApprovalRoute.AUTO, reason="R4: card placed under 72h monitoring"),
            ]
            if exposure_usd > 500.0:
                final_actions.append(ActionItem(action=PolicyAction.ESCALATE_TO_ANALYST, route=ApprovalRoute.AUTO, reason="R4: exposure exceeds $500 on unverified transaction"))
            change = "Customer challenge timed out without response; actions updated to decline transaction and elevate monitoring."
            return final_actions, change

        return initial_actions, "nothing"

    def build_sar(
        self,
        should_file: bool,
        reason: str,
        case_id: str,
        customer_id: str,
        card_id: str,
        affected_txn_ids: List[str],
        connected_cards: List[str],
        connected_devices: List[str],
        exposure_usd: float,
        activity_dates: List[str],
        narrative_detail: str,
    ) -> SAR:
        """Constructs the official SAR object compliant with FinCEN guidance."""
        if not should_file:
            return SAR(
                file=False,
                reason=reason or "Exposure under reporting threshold and no multi-party syndicate connection detected.",
                narrative="",
                subjects=[],
                total_amount_usd=0.0,
                activity_dates=[],
            )

        subjects = [customer_id, card_id] + connected_cards
        if connected_devices:
            subjects.extend(connected_devices[:2])

        narrative = (
            f"During the period {activity_dates[0]} to {activity_dates[-1]}, card {card_id} associated with customer {customer_id} "
            f"was subjected to unauthorized transaction activity totaling ${exposure_usd:.2f} across {len(affected_txn_ids)} transaction(s). "
            f"{narrative_detail} "
            f"The activity was flagged via TigerGraph graph traversal and verified under bank policy rules. "
            f"Card {card_id} has been blocked and marked for replacement. "
            f"Connected cards ({', '.join(connected_cards) if connected_cards else 'none'}) were identified and placed under monitoring to mitigate systemic exposure."
        )

        return SAR(
            file=True,
            reason=reason,
            narrative=narrative,
            subjects=subjects,
            total_amount_usd=round(exposure_usd, 2),
            activity_dates=activity_dates,
        )
