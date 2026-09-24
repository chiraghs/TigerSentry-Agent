"""
Benchmark Runner & Submission Answer Generator
Executes the agent across all 20 official Hacker House Goa exam cases
and saves compliant answer files into cases/<case_id>.json.
"""

import os
import json
import argparse
import logging
from src.agent.investigator import OfficialFraudInvestigator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BenchmarkRunner")


def generate_submission_cases(output_dir: str = "cases", verbose: bool = True):
    os.makedirs(output_dir, exist_ok=True)
    investigator = OfficialFraudInvestigator()
    case_pack = investigator.get_case_pack()

    print(f"\n========================================================")
    print(f"🚀 Running Investigation Agent on {len(case_pack)} Official Exam Cases")
    print(f"========================================================\n")

    summary = {
        "total_cases": len(case_pack),
        "fraud_count": 0,
        "legitimate_count": 0,
        "sar_filed_count": 0,
        "cases": [],
    }

    for c in case_pack:
        case_id = c["case_id"]
        ans = investigator.investigate_case(c)

        if ans.case.verdict.value == "fraud":
            summary["fraud_count"] += 1
        elif ans.case.verdict.value == "legitimate":
            summary["legitimate_count"] += 1

        if ans.sar.file:
            summary["sar_filed_count"] += 1

        # Write output file
        out_path = os.path.join(output_dir, f"{case_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(ans.model_dump(mode="json"), f, indent=2)

        summary["cases"].append({
            "case_id": case_id,
            "verdict": ans.case.verdict.value,
            "pattern": ans.case.pattern.value,
            "exposure_usd": ans.case.exposure_usd,
            "sar_file": ans.sar.file,
            "initial_actions": [a.action.value for a in ans.next_best_actions.initial],
            "final_actions": [a.action.value for a in ans.next_best_actions.final],
        })

        if verbose:
            init_acts = ",".join([a.action.value for a in ans.next_best_actions.initial])
            final_acts = ",".join([a.action.value for a in ans.next_best_actions.final])
            print(f"[{case_id}] Verdict: {ans.case.verdict.value.upper():10} | Pattern: {ans.case.pattern.value:25} | Exposure: ${ans.case.exposure_usd:8.2f} | SAR: {str(ans.sar.file):5} | Initial: {init_acts} -> Final: {final_acts}")

    print(f"\n✅ All {len(case_pack)} official answer files generated in: {output_dir}/")
    print(f"📊 Summary:")
    print(f"   - Confirmed Fraud: {summary['fraud_count']}")
    print(f"   - Cleared Legitimate: {summary['legitimate_count']}")
    print(f"   - SAR Filings: {summary['sar_filed_count']}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="cases", help="Directory for answer files")
    args = parser.parse_args()
    generate_submission_cases(output_dir=args.output_dir)
