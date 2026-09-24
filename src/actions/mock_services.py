"""
Controlled Actions and Mock Evidence Services
Provides simulation of policy-controlled external actions:
- Customer SMS transaction validation
- Step-up biometric / OTP authentication
- Fraud analyst interactive inquiry
- Account freezing, card blocking, customer warnings
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from src.agent.models import (
    ControlledEvidenceRequest,
    ControlledEvidenceResponse,
    SARReport,
)

logger = logging.getLogger("MockServices")


class MockEvidenceService:
    """Simulates interactive evidence collection from customer and internal systems."""

    def __init__(self):
        self.simulation_scenario = "DEFAULT"

    def set_simulation_scenario(self, scenario: str):
        """Allows testing deterministic outcomes like CONFIRMED_BY_USER, DENIED_BY_USER, MFA_FAILED."""
        self.simulation_scenario = scenario

    def request_customer_validation(
        self, customer_id: str, txn_id: str, amount: float
    ) -> ControlledEvidenceResponse:
        """Simulates sending an SMS or in-app push message to the cardholder to confirm a transaction."""
        logger.info(f"Dispatching customer validation push for customer={customer_id}, txn={txn_id}, amount=${amount}")

        if self.simulation_scenario == "USER_FRAUD_ALERT" or "fraud" in customer_id.lower():
            return ControlledEvidenceResponse(
                evidence_type="CUSTOMER_SMS_VALIDATION",
                status="SUCCESS",
                customer_confirmed_legitimate=False,
                latency_ms=420,
                notes="Customer responded: 'No, I did not authorize this charge! Please lock my card immediately.'",
            )
        elif self.simulation_scenario == "USER_CONFIRMED" or "legit" in customer_id.lower():
            return ControlledEvidenceResponse(
                evidence_type="CUSTOMER_SMS_VALIDATION",
                status="SUCCESS",
                customer_confirmed_legitimate=True,
                latency_ms=210,
                notes="Customer responded: 'Yes, this is my purchase while traveling.'",
            )
        elif self.simulation_scenario == "TIMEOUT":
            return ControlledEvidenceResponse(
                evidence_type="CUSTOMER_SMS_VALIDATION",
                status="TIMEOUT",
                customer_confirmed_legitimate=None,
                latency_ms=3000,
                notes="No response from customer within policy deadline (10 minutes).",
            )
        else:
            # Default heuristic based on transaction context
            return ControlledEvidenceResponse(
                evidence_type="CUSTOMER_SMS_VALIDATION",
                status="SUCCESS",
                customer_confirmed_legitimate=False if amount > 1000 else True,
                latency_ms=350,
                notes="Automated SMS verification response recorded.",
            )

    def request_step_up_auth(self, customer_id: str) -> ControlledEvidenceResponse:
        """Simulates 3D Secure / MFA challenge."""
        logger.info(f"Triggering 3DS step-up authentication challenge for customer={customer_id}")
        
        if self.simulation_scenario in ["MFA_FAILED", "USER_FRAUD_ALERT"]:
            return ControlledEvidenceResponse(
                evidence_type="STEP_UP_MFA",
                status="FAILED",
                mfa_passed=False,
                latency_ms=600,
                notes="Biometric verification failed; OTP retry limit reached.",
            )
        return ControlledEvidenceResponse(
            evidence_type="STEP_UP_MFA",
            status="SUCCESS",
            mfa_passed=True,
            latency_ms=310,
            notes="Biometric Passkey challenge successfully validated on trusted device.",
        )

    def request_analyst_review(self, case_id: str, inquiry: str) -> ControlledEvidenceResponse:
        """Simulates requesting senior fraud analyst input for complex/uncertain cases."""
        logger.info(f"Escalating inquiry to L2 Risk Analyst for case={case_id}: {inquiry}")
        return ControlledEvidenceResponse(
            evidence_type="ANALYST_INQUIRY",
            status="SUCCESS",
            analyst_finding="Analyst note: Prior IP address matches known VPN egress node used in credential stuffing attacks.",
            latency_ms=1200,
            notes="Manual triage completed.",
        )


class MockActionExecutionService:
    """Executes containment actions within predefined policy and approval requirements."""

    def __init__(self):
        self.action_history: list = []

    def block_card(self, card_id: str, reason: str, approval_by: str) -> Dict[str, Any]:
        record = {
            "action": "BLOCK_CARD",
            "target": card_id,
            "reason": reason,
            "approved_by": approval_by,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "EXECUTED",
        }
        self.action_history.append(record)
        logger.info(f"Action Executed: {record}")
        return record

    def freeze_account(self, account_id: str, reason: str, approval_by: str) -> Dict[str, Any]:
        record = {
            "action": "FREEZE_ACCOUNT",
            "target": account_id,
            "reason": reason,
            "approved_by": approval_by,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "EXECUTED",
        }
        self.action_history.append(record)
        logger.info(f"Action Executed: {record}")
        return record

    def send_customer_warning(self, customer_id: str, message: str) -> Dict[str, Any]:
        record = {
            "action": "WARN_CUSTOMER",
            "target": customer_id,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "DELIVERED",
        }
        self.action_history.append(record)
        logger.info(f"Action Executed: {record}")
        return record

    def file_sar(self, sar: SARReport) -> Dict[str, Any]:
        record = {
            "action": "FILE_SAR",
            "sar_id": sar.sar_id,
            "subject_id": sar.subject_id,
            "amount": sar.total_suspicious_amount,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "TRANSMITTED_TO_FINCEN",
        }
        self.action_history.append(record)
        logger.info(f"SAR Filed: {record}")
        return record
