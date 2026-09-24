"""
State definition for the autonomous fraud investigation agent.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.agent.models import (
    TriggerEvent,
    GraphEvidence,
    FraudPatternType,
    PolicyRuleMatch,
    NextBestAction,
    ControlledEvidenceRequest,
    ControlledEvidenceResponse,
    SARReport,
)


class InvestigationState(BaseModel):
    case_id: str
    current_step: int = 1
    trigger: TriggerEvent
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Evidence & Analysis
    graph_evidence: Optional[GraphEvidence] = None
    historical_cases: List[Dict[str, Any]] = Field(default_factory=list)
    identified_patterns: List[FraudPatternType] = Field(default_factory=list)
    policy_matches: List[PolicyRuleMatch] = Field(default_factory=list)
    
    # Uncertainty quantification
    risk_score: float = 0.0
    confidence_score: float = 0.0
    uncertainty_score: float = 1.0
    enough_evidence_to_act: bool = False
    
    # Hackathon Required Two-Stage Decisions
    nba_pre_evidence: Optional[NextBestAction] = None
    requested_evidence: Optional[ControlledEvidenceRequest] = None
    received_evidence: Optional[ControlledEvidenceResponse] = None
    nba_post_evidence: Optional[NextBestAction] = None
    
    # Compliance & Persistence
    sar_report: Optional[SARReport] = None
    graph_persisted: bool = False
    
    # Narrative & Audit
    investigation_log: List[str] = Field(default_factory=list)
    executive_summary: str = ""
    reasoning_explanation: str = ""

    def log(self, message: str):
        self.investigation_log.append(f"[{datetime.utcnow().isoformat()}] Step {self.current_step}: {message}")
