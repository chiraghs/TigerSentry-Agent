from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TriggerType(str, Enum):
    RISK_SCORE = "RISK_SCORE"
    CUSTOMER_REPORT = "CUSTOMER_REPORT"
    ANALYST_REQUEST = "ANALYST_REQUEST"
    VELOCITY_ALERT = "VELOCITY_ALERT"


class ActionType(str, Enum):
    ALLOW_TRANSACTION = "ALLOW_TRANSACTION"
    MONITOR_ACCOUNT = "MONITOR_ACCOUNT"
    WARN_CUSTOMER = "WARN_CUSTOMER"
    REQUEST_STEP_UP_AUTH = "REQUEST_STEP_UP_AUTH"
    REQUEST_CUSTOMER_CONFIRMATION = "REQUEST_CUSTOMER_CONFIRMATION"
    BLOCK_CARD = "BLOCK_CARD"
    FREEZE_ACCOUNT = "FREEZE_ACCOUNT"
    FILE_SAR = "FILE_SAR"
    ESCALATE_TO_ANALYST = "ESCALATE_TO_ANALYST"
    CLOSE_CASE = "CLOSE_CASE"


class ApprovalRoute(str, Enum):
    AUTOMATED = "AUTOMATED"
    L1_FRAUD_ANALYST = "L1_FRAUD_ANALYST"
    L2_RISK_MANAGER = "L2_RISK_MANAGER"
    COMPLIANCE_LEGAL = "COMPLIANCE_LEGAL"


class FraudPatternType(str, Enum):
    CARD_TESTING_VELOCITY = "CARD_TESTING_VELOCITY"
    DEVICE_IDENTITY_RING = "DEVICE_IDENTITY_RING"
    IMPOSSIBLE_TRAVEL = "IMPOSSIBLE_TRAVEL"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    MERCHANT_COLLUSION = "MERCHANT_COLLUSION"
    UNKNOWN_ANOMALOUS = "UNKNOWN_ANOMALOUS"


class Transaction(BaseModel):
    txn_id: str
    amount: float
    timestamp: datetime
    model_risk_score: float = Field(ge=0.0, le=1.0)
    customer_id: str
    card_id: str
    merchant_id: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    country: Optional[str] = "US"
    city: Optional[str] = None
    is_online: bool = True
    attributes: Dict[str, Any] = Field(default_factory=dict)


class TriggerEvent(BaseModel):
    trigger_id: str
    trigger_type: TriggerType
    transaction: Transaction
    source: str = "Real-time Scoring Gateway"
    initial_notes: Optional[str] = None


class GraphEvidence(BaseModel):
    shared_device_card_count: int = 0
    shared_device_customer_count: int = 0
    shared_ip_customer_count: int = 0
    velocity_1h_txn_count: int = 0
    velocity_1h_amount: float = 0.0
    impossible_travel_detected: bool = False
    travel_speed_kmh: Optional[float] = None
    prior_closed_fraud_cases: int = 0
    prior_cleared_cases: int = 0
    connected_blacklisted_entities: List[str] = Field(default_factory=list)
    raw_subgraph_nodes: int = 0
    raw_subgraph_edges: int = 0


class PolicyRuleMatch(BaseModel):
    rule_id: str
    rule_name: str
    severity: str  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    description: str
    regulatory_reference: Optional[str] = None


class NextBestAction(BaseModel):
    action: ActionType
    approval_route: ApprovalRoute
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    policy_citation: Optional[str] = None


class ControlledEvidenceRequest(BaseModel):
    evidence_type: str  # CUSTOMER_SMS_VALIDATION, STEP_UP_MFA, ANALYST_INQUIRY
    target_entity: str
    request_details: Dict[str, Any] = Field(default_factory=dict)
    sent_at: datetime = Field(default_factory=datetime.utcnow)


class ControlledEvidenceResponse(BaseModel):
    evidence_type: str
    status: str  # SUCCESS, FAILED, TIMEOUT, DENIED
    customer_confirmed_legitimate: Optional[bool] = None
    mfa_passed: Optional[bool] = None
    analyst_finding: Optional[str] = None
    latency_ms: int = 150
    notes: Optional[str] = None


class SARReport(BaseModel):
    sar_id: str
    subject_id: str
    narrative: str
    suspected_violations: List[str]
    total_suspicious_amount: float
    filing_deadline_days: int = 30
    requires_law_enforcement_escalation: bool = False


class InvestigationAnswerFile(BaseModel):
    case_id: str
    trigger: TriggerEvent
    investigation_record: Dict[str, Any]
    graph_evidence: GraphEvidence
    identified_patterns: List[FraudPatternType]
    uncertainty_level: float
    
    # Required Hackathon NBA fields
    nba_pre_evidence: NextBestAction
    requested_evidence: Optional[ControlledEvidenceRequest] = None
    received_evidence: Optional[ControlledEvidenceResponse] = None
    nba_post_evidence: NextBestAction
    
    sar_report: Optional[SARReport] = None
    graph_persistence_confirmed: bool = False
    executive_summary: str
    reasoning_explanation: str
