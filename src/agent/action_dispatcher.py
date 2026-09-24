"""
TigerSentry Action Dispatcher — Downstream Mock Banking & API Integration Hub
Simulates execution across Core Banking CMS, CRM, FinCEN Gateway, and Payment Networks
per the Hackathon Action Execution specification.
"""

import time
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone


class ActionDispatcher:
    """
    Simulates real-world execution against core banking and regulatory APIs:
    - Card Management System (CMS) / Visa / Mastercard Network
    - Core Banking Deposit Accounts (Freeze / Unfreeze)
    - CRM Systems (Salesforce Financial Services Cloud)
    - Regulatory FinCEN BSA E-Filing Gateway
    - Fraud Ops Case Graph Management (TigerGraph Savanna)
    - Cardholder Messaging (Apple Push / Twilio SMS)
    """

    @staticmethod
    def execute_action(action: str, case_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        now = datetime.now(timezone.utc).isoformat()
        trace_id = f"TRC-{uuid.uuid4().hex[:8].upper()}"

        if action in ("BLOCK_CARD", "BLOCK_ALL_CARDS"):
            card_id = context.get("card_id", "CARD-PRIMARY")
            return {
                "action": action,
                "system": "Core Banking Card Management System (CMS)",
                "status": "EXECUTED",
                "http_status": 200,
                "latency_ms": 38,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "card_id": card_id,
                    "previous_state": "ACTIVE",
                    "new_state": "BLOCKED_SUSPECTED_FRAUD",
                    "visa_network_alert_sent": True,
                    "replacement_card_queued": True,
                },
                "log": f"Card {card_id} locked across payment networks. PIN and CVV disabled.",
            }

        elif action in ("ALLOW_TRANSACTION", "CLOSE_NO_FRAUD"):
            txn_id = context.get("txn_id", "TXN-01")
            return {
                "action": action,
                "system": "Payment Gateway & Authorization Gateway",
                "status": "EXECUTED",
                "http_status": 200,
                "latency_ms": 22,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "txn_id": txn_id,
                    "authorization_status": "APPROVED",
                    "settlement_hold_released": True,
                    "fraud_flag_cleared": True,
                },
                "log": f"Transaction {txn_id} security hold released. Funds settled.",
            }

        elif action == "FREEZE_ACCOUNT":
            cust_id = context.get("customer_id", "CUST-01")
            return {
                "action": action,
                "system": "Core Banking Account Ledger (Deposit Core)",
                "status": "EXECUTED",
                "http_status": 200,
                "latency_ms": 55,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "customer_id": cust_id,
                    "debit_postings_allowed": False,
                    "credit_postings_allowed": True,
                    "wire_transfers_halted": True,
                },
                "log": f"Customer account {cust_id} frozen for emergency containment.",
            }

        elif action == "FILE_REPORT":
            exposure = context.get("exposure_usd", 0.0)
            return {
                "action": action,
                "system": "FinCEN BSA E-Filing System (Secure Gateway)",
                "status": "SUBMITTED",
                "http_status": 201,
                "latency_ms": 115,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "bsa_tracking_id": f"BSA-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}",
                    "filing_institution": "TigerSentry National Bank (Partner Node)",
                    "report_type": "FinCEN SAR Form 111",
                    "total_amount_usd": exposure,
                    "status": "ACCEPTED_BY_REGULATOR",
                },
                "log": f"Suspicious Activity Report submitted to FinCEN with acknowledgement.",
            }

        elif action == "CREATE_CASE":
            return {
                "action": action,
                "system": "TigerGraph Savanna & CRM Case Management",
                "status": "COMMITTED",
                "http_status": 200,
                "latency_ms": 18,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "graph_node_id": f"TG-CASE-{case_id}",
                    "salesforce_case_number": f"SF-CASE-{case_id}",
                    "assigned_queue": "L1_FRAUD_OPERATIONS",
                    "priority": "HIGH",
                },
                "log": f"Fraud case registered in TigerGraph graph database and synchronized to CRM.",
            }

        elif action == "MONITOR_CONNECTED_CARDS":
            cards = context.get("connected_card_ids", [])
            return {
                "action": action,
                "system": "Real-time Scoring Gateway (Streaming Rules Engine)",
                "status": "MONITORING_ACTIVE",
                "http_status": 200,
                "latency_ms": 25,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "cards_monitored": cards,
                    "monitoring_window_hours": 72,
                    "velocity_threshold_override": 0.35,
                },
                "log": f"Placed {len(cards)} connected cards on 72h elevated security monitoring.",
            }

        elif action in ("VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH"):
            return {
                "action": action,
                "system": "Apple Push Notification Service (APNs) & Twilio Gateway",
                "status": "DISPATCHED",
                "http_status": 202,
                "latency_ms": 19,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "channel": "APNs_SECURE_ENCLAVE",
                    "delivered": True,
                    "challenge_timeout_seconds": 600,
                },
                "log": "2-Factor cryptographic challenge dispatched to registered device.",
            }

        elif action == "REFUND_CUSTOMER":
            amount = context.get("exposure_usd", 0.0)
            return {
                "action": action,
                "system": "Cardholder Dispute & Reimbursement Ledger",
                "status": "CREDITED",
                "http_status": 200,
                "latency_ms": 78,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {
                    "provisional_credit_issued": True,
                    "amount_usd": amount,
                    "reimbursement_reference": f"REF-{uuid.uuid4().hex[:8].upper()}",
                },
                "log": f"Provisional reimbursement of ${amount:.2f} credited to cardholder account.",
            }

        else:
            return {
                "action": action,
                "system": "TigerSentry General Dispatcher",
                "status": "EXECUTED",
                "http_status": 200,
                "latency_ms": 15,
                "trace_id": trace_id,
                "timestamp": now,
                "response": {"action": action, "result": "PROCESSED"},
                "log": f"Action {action} dispatched to bank execution pipeline.",
            }

    @classmethod
    def execute_all(cls, actions: List[str], case_id: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        results = []
        for act in actions:
            results.append(cls.execute_action(act, case_id, context))
        return results
