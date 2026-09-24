"""
GraphRAG & Policy Grounding Engine
Encapsulates bank fraud policies, the 5 known fraud patterns,
regulatory reporting triggers (SAR), and provides contextual prompt grounding.
"""

from typing import Dict, Any, List, Tuple
from src.agent.models import (
    PolicyRuleMatch,
    FraudPatternType,
    GraphEvidence,
    SARReport,
    ApprovalRoute,
    ActionType,
    Transaction,
)


class PolicyEngine:
    """Evaluates transactions and graph evidence against bank fraud policies and typologies."""

    KNOWN_PATTERNS = {
        FraudPatternType.CARD_TESTING_VELOCITY: {
            "name": "Card Testing Velocity",
            "description": "Rapid succession of multiple transactions testing card validity.",
            "threshold_txns_1h": 5,
            "risk_score_min": 0.65,
        },
        FraudPatternType.DEVICE_IDENTITY_RING: {
            "name": "Device Identity Ring",
            "description": "Single device or IP footprint shared across multiple unrelated accounts/cards.",
            "threshold_shared_cards": 3,
            "threshold_shared_customers": 2,
        },
        FraudPatternType.IMPOSSIBLE_TRAVEL: {
            "name": "Impossible Travel",
            "description": "Consecutive transactions separated by distance requiring impossible transit speed (>800 km/h).",
            "speed_threshold_kmh": 800.0,
        },
        FraudPatternType.ACCOUNT_TAKEOVER: {
            "name": "Account Takeover (ATO)",
            "description": "High-amount transactions originating from unrecognized device/IP on established account.",
            "amount_threshold": 800.0,
        },
        FraudPatternType.MERCHANT_COLLUSION: {
            "name": "Merchant Collusion / Bust-Out",
            "description": "Transactions concentrated at flagged high-risk merchants with history of fraudulent disputes.",
        },
    }

    BANK_POLICIES = [
        {
            "id": "POL-101",
            "name": "High Risk Containment",
            "condition": "Risk score >= 0.85 OR active device ring >= 3 cards",
            "mandated_action": ActionType.BLOCK_CARD,
            "approval": ApprovalRoute.AUTOMATED,
            "regulatory_ref": "Internal Risk Policy Sec 4.1",
        },
        {
            "id": "POL-102",
            "name": "Controlled Customer Verification",
            "condition": "Moderate risk (0.40 <= risk <= 0.84) with high uncertainty",
            "mandated_action": ActionType.REQUEST_CUSTOMER_CONFIRMATION,
            "approval": ApprovalRoute.AUTOMATED,
            "regulatory_ref": "Customer Authentication Guidelines (FFIEC)",
        },
        {
            "id": "POL-103",
            "name": "Senior Management Approval for Account Freeze",
            "condition": "Account-level freeze requested",
            "mandated_action": ActionType.FREEZE_ACCOUNT,
            "approval": ApprovalRoute.L2_RISK_MANAGER,
            "regulatory_ref": "Bank Operational Risk Policy Sec 8.2",
        },
        {
            "id": "POL-104",
            "name": "Mandatory SAR Filing",
            "condition": "Confirmed or strongly suspected fraud with cumulative exposure >= $5,000",
            "mandated_action": ActionType.FILE_SAR,
            "approval": ApprovalRoute.COMPLIANCE_LEGAL,
            "regulatory_ref": "FinCEN BSA 31 CFR 1020.320",
        },
    ]

    def evaluate_graph_patterns(self, evidence: GraphEvidence, txn: Transaction) -> List[FraudPatternType]:
        """Detects presence of any of the 5 known fraud typologies."""
        detected = []

        # 1. Device Ring
        if (
            evidence.shared_device_card_count >= self.KNOWN_PATTERNS[FraudPatternType.DEVICE_IDENTITY_RING]["threshold_shared_cards"]
            or evidence.shared_device_customer_count >= self.KNOWN_PATTERNS[FraudPatternType.DEVICE_IDENTITY_RING]["threshold_shared_customers"]
        ):
            detected.append(FraudPatternType.DEVICE_IDENTITY_RING)

        # 2. Velocity
        if (
            evidence.velocity_1h_txn_count >= self.KNOWN_PATTERNS[FraudPatternType.CARD_TESTING_VELOCITY]["threshold_txns_1h"]
            or txn.model_risk_score > 0.80
        ):
            detected.append(FraudPatternType.CARD_TESTING_VELOCITY)

        # 3. Impossible Travel
        if evidence.impossible_travel_detected:
            detected.append(FraudPatternType.IMPOSSIBLE_TRAVEL)

        # 4. ATO
        if txn.amount > 1000.0 and evidence.shared_ip_customer_count > 1:
            detected.append(FraudPatternType.ACCOUNT_TAKEOVER)

        if not detected and txn.model_risk_score > 0.50:
            detected.append(FraudPatternType.UNKNOWN_ANOMALOUS)

        return detected

    def evaluate_policy_matches(self, patterns: List[FraudPatternType], txn: Transaction, evidence: GraphEvidence) -> List[PolicyRuleMatch]:
        """Maps detected patterns and transaction attributes to formal policy rules."""
        matches = []

        if txn.model_risk_score >= 0.85 or FraudPatternType.DEVICE_IDENTITY_RING in patterns:
            matches.append(
                PolicyRuleMatch(
                    rule_id="POL-101",
                    rule_name="High Risk Immediate Containment",
                    severity="HIGH",
                    description="Transaction model risk score >= 0.85 or linked to multi-card device ring.",
                    regulatory_reference="Internal Risk Policy Sec 4.1",
                )
            )

        if 0.40 <= txn.model_risk_score < 0.85 and not (FraudPatternType.DEVICE_IDENTITY_RING in patterns):
            matches.append(
                PolicyRuleMatch(
                    rule_id="POL-102",
                    rule_name="Controlled Customer Verification",
                    severity="MEDIUM",
                    description="Moderate risk transaction requires step-up authentication or SMS confirmation before hard block.",
                    regulatory_reference="FFIEC Customer Authentication Guidelines",
                )
            )

        if txn.amount >= 5000.0 or evidence.velocity_1h_amount >= 5000.0:
            matches.append(
                PolicyRuleMatch(
                    rule_id="POL-104",
                    rule_name="Mandatory SAR Threshold Met",
                    severity="CRITICAL",
                    description="Aggregate fraud exposure >= $5,000 requires BSA filing.",
                    regulatory_reference="FinCEN BSA 31 CFR 1020.320",
                )
            )

        return matches

    def generate_sar_if_warranted(self, case_id: str, txn: Transaction, evidence: GraphEvidence, patterns: List[FraudPatternType]) -> Tuple[bool, SARReport | None]:
        """Assesses whether policy requires filing a Suspicious Activity Report (SAR)."""
        exposure = max(txn.amount, evidence.velocity_1h_amount)
        sar_required = exposure >= 5000.0 or FraudPatternType.DEVICE_IDENTITY_RING in patterns

        if not sar_required:
            return False, None

        sar = SARReport(
            sar_id=f"SAR-{case_id}-{int(txn.amount)}",
            subject_id=txn.customer_id,
            narrative=(
                f"Suspicious activity detected regarding customer {txn.customer_id} on card {txn.card_id}. "
                f"Transaction {txn.txn_id} for amount ${txn.amount:.2f} demonstrated patterns: "
                f"{', '.join([p.value for p in patterns])}. TigerGraph analysis uncovered "
                f"{evidence.shared_device_card_count} connected cards and {evidence.shared_device_customer_count} "
                f"connected customer entities operating across shared infrastructure."
            ),
            suspected_violations=[p.value for p in patterns],
            total_suspicious_amount=exposure,
            filing_deadline_days=30,
            requires_law_enforcement_escalation=exposure >= 25000.0,
        )
        return True, sar

    def format_graphrag_context(self, txn: Transaction, evidence: GraphEvidence, patterns: List[FraudPatternType], similar_cases: List[Dict[str, Any]]) -> str:
        """Formats integrated Graph context + Policy text into a grounded prompt context."""
        context = []
        context.append(f"=== TARGET TRANSACTION: {txn.txn_id} ===")
        context.append(f"Amount: ${txn.amount:.2f} | Customer: {txn.customer_id} | Risk Score: {txn.model_risk_score:.2f}")
        context.append(f"Card: {txn.card_id} | Location: {txn.city}, {txn.country}")
        context.append("\n=== TIGERGRAPH KNOWLEDGE GRAPH EVIDENCE ===")
        context.append(f"- Connected cards on same device: {evidence.shared_device_card_count}")
        context.append(f"- Connected customers on same device: {evidence.shared_device_customer_count}")
        context.append(f"- Rolling 1-hour velocity: {evidence.velocity_1h_txn_count} txns, total ${evidence.velocity_1h_amount:.2f}")
        context.append(f"- Impossible travel detected: {evidence.impossible_travel_detected} (Speed: {evidence.travel_speed_kmh or 0} km/h)")
        context.append(f"- 2-hop Subgraph entities: {evidence.raw_subgraph_nodes} nodes, {evidence.raw_subgraph_edges} edges")

        if similar_cases:
            context.append("\n=== HISTORICAL CASE MEMORY (PAST 4 MONTHS) ===")
            for c in similar_cases:
                context.append(f"- Case {c.get('case_id')}: Typology={c.get('fraud_type')}, Outcome={c.get('outcome')}, Action={c.get('final_action')}")

        context.append("\n=== IDENTIFIED FRAUD TYPOLOGIES ===")
        for p in patterns:
            context.append(f"- {p.value}: {self.KNOWN_PATTERNS.get(p, {}).get('description', '')}")

        return "\n".join(context)
