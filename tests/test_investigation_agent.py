"""
Tests for OfficialFraudInvestigator running 8-step lifecycle investigations.
"""

from src.agent.investigator import OfficialFraudInvestigator
from src.agent.models import CaseVerdict, CaseStatus, FraudPattern, PolicyAction


def test_investigate_case_hhg_001():
    inv = OfficialFraudInvestigator()
    case_pack = inv.get_case_pack()
    assert len(case_pack) == 20
    
    meta_01 = case_pack[0]
    assert meta_01["case_id"] == "HHG-001"
    
    ans = inv.investigate_case(meta_01)
    assert ans.case_id == "HHG-001"
    assert ans.case.exposure_usd > 0
    assert len(ans.next_best_actions.initial) > 0
    assert len(ans.next_best_actions.final) > 0
    assert ans.sar is not None
    assert ans.case.written_to_graph is True
    assert ans.case.graph_case_id == "TG-CASE-HHG-001"


def test_investigate_case_verdicts():
    inv = OfficialFraudInvestigator()
    case_pack = inv.get_case_pack()
    
    # Run across cases
    for meta in case_pack[:3]:
        ans = inv.investigate_case(meta)
        assert ans.case_id == meta["case_id"]
        assert ans.case.verdict in [CaseVerdict.FRAUD, CaseVerdict.LEGITIMATE, CaseVerdict.UNCERTAIN]
        assert ans.case.status in [CaseStatus.CLOSED_FRAUD, CaseStatus.CLOSED_LEGITIMATE, CaseStatus.ESCALATED, CaseStatus.OPEN]
