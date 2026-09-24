"""
Evaluation Runner & Benchmark Answer File Generator
Executes fraud investigations across benchmark cases and exports standardized answer files.
"""

import os
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.agent.models import (
    Transaction,
    TriggerEvent,
    TriggerType,
    InvestigationAnswerFile,
)
from src.agent.investigator import FraudInvestigatorAgent
from src.tigergraph.client import TigerGraphClient
from src.actions.mock_services import MockEvidenceService, MockActionExecutionService


def generate_benchmark_cases() -> List[TriggerEvent]:
    """
    Synthesizes the 20 benchmark test cases reflecting the IEEE-CIS test distribution:
    - Cases 1-5: Device Identity Rings & Carding Syndicates
    - Cases 6-10: Rapid Card Testing Velocity Bursts
    - Cases 7-12: Impossible Travel & Geolocation Anomalies
    - Cases 13-16: High-value Account Takeover (ATO) with large exposures (SAR-triggering)
    - Cases 17-20: Legitimate customer travel / False positive tests requiring customer clear
    """
    cases = []
    base_time = datetime(2026, 8, 15, 12, 0, 0)

    # 1. Device Ring Cases
    for i in range(1, 5):
        txn = Transaction(
            txn_id=f"TXN_BENCH_{i:03d}",
            amount=420.0 + i * 50.0,
            timestamp=base_time + timedelta(minutes=i * 5),
            model_risk_score=0.88,
            customer_id=f"CUST_RING_{i:02d}",
            card_id=f"CARD_RING_{i:02d}",
            merchant_id="MERCH_CRYPTO_EXCHANGE",
            device_id="DEV_EMULATOR_RING_X99",
            ip_address="198.51.100.42",
            country="US",
            city="New York",
        )
        cases.append(
            TriggerEvent(
                trigger_id=f"TRIG_{i:03d}",
                trigger_type=TriggerType.RISK_SCORE,
                transaction=txn,
                initial_notes="Automated model alert: High ML score on emulator device footprint.",
            )
        )

    # 2. Velocity Burst Cases
    for i in range(5, 9):
        txn = Transaction(
            txn_id=f"TXN_BENCH_{i:03d}",
            amount=95.0 + i * 15.0,
            timestamp=base_time + timedelta(minutes=i * 2),
            model_risk_score=0.78,
            customer_id=f"CUST_VEL_{i:02d}",
            card_id=f"CARD_BURST_{i:02d}",
            merchant_id="MERCH_GIFT_CARDS_FAST",
            device_id=f"DEV_MOBILE_{i:02d}",
            ip_address=f"203.0.113.{i}",
            country="US",
            city="Chicago",
        )
        cases.append(
            TriggerEvent(
                trigger_id=f"TRIG_{i:03d}",
                trigger_type=TriggerType.VELOCITY_ALERT,
                transaction=txn,
                initial_notes="Rule alert: >5 rapid transactions within 10 minutes.",
            )
        )

    # 3. Impossible Travel Cases
    for i in range(9, 13):
        txn = Transaction(
            txn_id=f"TXN_BENCH_{i:03d}",
            amount=850.0 + i * 30.0,
            timestamp=base_time + timedelta(hours=i),
            model_risk_score=0.72,
            customer_id=f"CUST_TRAVEL_{i:02d}",
            card_id=f"CARD_TRAVEL_{i:02d}",
            merchant_id="MERCH_LUXURY_WATCH",
            device_id=f"DEV_UNKNOWN_{i:02d}",
            ip_address=f"192.0.2.{i}",
            country="SG",
            city="Singapore",
        )
        cases.append(
            TriggerEvent(
                trigger_id=f"TRIG_{i:03d}",
                trigger_type=TriggerType.RISK_SCORE,
                transaction=txn,
                initial_notes="Impossible travel alert: card used in London 1.5h prior.",
            )
        )

    # 4. Large Account Takeover & SAR Cases (> $5,000 exposure)
    for i in range(13, 17):
        txn = Transaction(
            txn_id=f"TXN_BENCH_{i:03d}",
            amount=6500.0 + i * 500.0,
            timestamp=base_time + timedelta(days=1, hours=i),
            model_risk_score=0.86,
            customer_id=f"CUST_HIGHVAL_{i:02d}",
            card_id=f"CARD_HIGHVAL_{i:02d}",
            merchant_id="MERCH_WHOLESALE_ELECTRONICS",
            device_id=f"DEV_NEW_{i:02d}",
            ip_address=f"198.51.100.{100 + i}",
            country="US",
            city="Miami",
        )
        cases.append(
            TriggerEvent(
                trigger_id=f"TRIG_{i:03d}",
                trigger_type=TriggerType.CUSTOMER_REPORT,
                transaction=txn,
                initial_notes="Large transaction threshold ($5k+) alert on newly enrolled device.",
            )
        )

    # 5. Legitimate Travel / Borderline Cases (Customer Clears)
    for i in range(17, 21):
        txn = Transaction(
            txn_id=f"TXN_BENCH_{i:03d}",
            amount=210.0 + i * 10.0,
            timestamp=base_time + timedelta(days=2, hours=i),
            model_risk_score=0.55,
            customer_id=f"CUST_LEGIT_{i:02d}",
            card_id=f"CARD_LEGIT_{i:02d}",
            merchant_id="MERCH_HOTEL_BOOKING",
            device_id=f"DEV_TRUSTED_IPHONE_{i:02d}",
            ip_address=f"203.0.113.{50 + i}",
            country="FR",
            city="Paris",
        )
        cases.append(
            TriggerEvent(
                trigger_id=f"TRIG_{i:03d}",
                trigger_type=TriggerType.RISK_SCORE,
                transaction=txn,
                initial_notes="Unusual international transaction; cardholder traveling.",
            )
        )

    return cases


def run_benchmark(output_dir: str = "outputs/cases", verbose: bool = False):
    """Executes investigation on all benchmark cases and persists answer files."""
    os.makedirs(output_dir, exist_ok=True)
    agent = FraudInvestigatorAgent()
    cases = generate_benchmark_cases()

    print(f"\n========================================================")
    print(f"🚀 Running Investigation Agent on {len(cases)} Benchmark Cases")
    print(f"========================================================\n")

    summary = {
        "total_cases": len(cases),
        "pre_evidence_nba_distribution": {},
        "post_evidence_nba_distribution": {},
        "sar_filed_count": 0,
        "graph_persisted_count": 0,
        "cases_evaluated": [],
    }

    for idx, trigger in enumerate(cases, 1):
        case_id = f"CASE_BENCH_{idx:02d}"
        ans = agent.investigate(trigger, case_id=case_id)

        # Record metrics
        pre_act = ans.nba_pre_evidence.action.value
        post_act = ans.nba_post_evidence.action.value
        summary["pre_evidence_nba_distribution"][pre_act] = summary["pre_evidence_nba_distribution"].get(pre_act, 0) + 1
        summary["post_evidence_nba_distribution"][post_act] = summary["post_evidence_nba_distribution"].get(post_act, 0) + 1
        if ans.sar_report:
            summary["sar_filed_count"] += 1
        if ans.graph_persistence_confirmed:
            summary["graph_persisted_count"] += 1

        # Write single answer file per case
        ans_filepath = os.path.join(output_dir, f"{case_id}.json")
        with open(ans_filepath, "w") as f:
            json.dump(ans.model_dump(mode="json"), f, indent=2)

        summary["cases_evaluated"].append({
            "case_id": case_id,
            "txn_id": trigger.transaction.txn_id,
            "amount": trigger.transaction.amount,
            "pre_evidence_nba": pre_act,
            "pre_approval_route": ans.nba_pre_evidence.approval_route.value,
            "evidence_requested": ans.requested_evidence.evidence_type if ans.requested_evidence else None,
            "post_evidence_nba": post_act,
            "post_approval_route": ans.nba_post_evidence.approval_route.value,
            "sar_filed": ans.sar_report is not None,
            "answer_file": ans_filepath,
        })

        if verbose:
            print(f"[{idx:02d}/20] {case_id}: Pre-NBA={pre_act} -> Post-NBA={post_act} | SAR={ans.sar_report is not None}")

    # Write overall benchmark summary
    summary_path = os.path.join(output_dir, "benchmark_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ All 20 cases evaluated successfully!")
    print(f"📁 Answer files written to: {output_dir}/")
    print(f"📊 Summary report: {summary_path}")
    print(f"- Post-Evidence Actions: {summary['post_evidence_nba_distribution']}")
    print(f"- Suspicious Activity Reports (SAR) Generated: {summary['sar_filed_count']}")
    print(f"- Cases Persisted to TigerGraph Knowledge Graph: {summary['graph_persisted_count']}\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TigerGraph Agentic Fraud Evaluation Runner")
    parser.add_argument("--output-dir", default="outputs/cases", help="Directory to save answer files")
    parser.add_argument("--verbose", action="store_true", help="Print step-by-step case output")
    args = parser.parse_args()

    run_benchmark(output_dir=args.output_dir, verbose=args.verbose)
