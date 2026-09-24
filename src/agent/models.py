"""
Pydantic Domain Models matching the official Hacker House Goa Answer Format.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    OPEN = "open"
    CLOSED_FRAUD = "closed_fraud"
    CLOSED_LEGITIMATE = "closed_legitimate"
    ESCALATED = "escalated"


class CaseVerdict(str, Enum):
    FRAUD = "fraud"
    LEGITIMATE = "legitimate"
    UNCERTAIN = "uncertain"


class FraudPattern(str, Enum):
    CARD_TESTING = "card_testing"
    CARD_NOT_PRESENT_FRAUD = "card_not_present_fraud"
    CARD_NOT_PRESENT_NEW_DEVICE = "card_not_present_new_device"
    OUT_OF_REGION_USE = "out_of_region_use"
    ACCOUNT_TAKEOVER = "account_takeover"
    UNDOCUMENTED = "undocumented"
    NONE = "none"


class PolicyAction(str, Enum):
    ALLOW_TRANSACTION = "ALLOW_TRANSACTION"
    DECLINE_TRANSACTION = "DECLINE_TRANSACTION"
    MONITOR_CARD = "MONITOR_CARD"
    MONITOR_CONNECTED_CARDS = "MONITOR_CONNECTED_CARDS"
    WARN_CUSTOMER = "WARN_CUSTOMER"
    VERIFY_WITH_CUSTOMER = "VERIFY_WITH_CUSTOMER"
    STEP_UP_AUTH = "STEP_UP_AUTH"
    BLOCK_CARD = "BLOCK_CARD"
    BLOCK_ALL_CARDS = "BLOCK_ALL_CARDS"
    GENERATE_REPORT = "GENERATE_REPORT"
    CREATE_CASE = "CREATE_CASE"
    FILE_REPORT = "FILE_REPORT"
    ESCALATE_TO_ANALYST = "ESCALATE_TO_ANALYST"
    CLOSE_NO_FRAUD = "CLOSE_NO_FRAUD"


class ApprovalRoute(str, Enum):
    AUTO = "auto"
    L1 = "L1"
    L2 = "L2"


class EvidenceItem(BaseModel):
    claim: str
    source: str  # graph | document | customer | external
    ref: str
    entity_ids: List[str] = Field(default_factory=list)


class CaseRecord(BaseModel):
    status: CaseStatus
    verdict: CaseVerdict
    fraud_probability: float = Field(ge=0.0, le=1.0)
    pattern: FraudPattern
    pattern_description: str = ""
    affected_txn_ids: List[str] = Field(default_factory=list)
    first_suspicious_txn_id: str = ""
    connected_card_ids: List[str] = Field(default_factory=list)
    connected_device_profiles: List[str] = Field(default_factory=list)
    exposure_usd: float = 0.0
    evidence: List[EvidenceItem] = Field(default_factory=list)
    similar_prior_cases: List[str] = Field(default_factory=list)
    summary: str
    written_to_graph: bool = True
    graph_case_id: str = ""


class EvidenceRequest(BaseModel):
    type: str  # customer_validation | step_up_auth | analyst_info
    asked_after_step: int
    assumed_response: str


class ActionItem(BaseModel):
    action: PolicyAction
    route: ApprovalRoute
    reason: str


class NextBestActions(BaseModel):
    initial: List[ActionItem]
    final: List[ActionItem]
    what_changed: str


class SAR(BaseModel):
    file: bool
    reason: str
    narrative: str
    subjects: List[str] = Field(default_factory=list)
    total_amount_usd: float = 0.0
    activity_dates: List[str] = Field(default_factory=list)


class OfficialAnswerFile(BaseModel):
    case_id: str
    case: CaseRecord
    evidence_requests: List[EvidenceRequest] = Field(default_factory=list)
    next_best_actions: NextBestActions
    sar: SAR
    stop_reason: str
    tool_calls: int = 5
    tokens: int = 4200
    latency_s: float = 1.25


# Internal Trigger Definition
class TriggerItem(BaseModel):
    case_id: str
    opened_at: str
    trigger_type: str
    trigger_text: str
    flagged_txn_id: str
    card_id: str
    customer_id: str
    risk_score: Optional[float] = None
