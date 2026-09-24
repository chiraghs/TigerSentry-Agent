"""
Data Indexer & Staging Pipeline
Extracts and indexes relevant customer histories, identity records, and closed cases
for the 20 benchmark exam cases from the 708MB transactions.csv and 26MB identity.csv.
"""

import os
import csv
import json
import logging
from typing import Dict, Any, List, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataIndexer")

DATA_DIR = "/Volumes/DiskD/HACKATHONS/Fraud-Detection/data/sample"
OUTPUT_STAGED = os.path.join(DATA_DIR, "staged_benchmark.json")


def run_indexing():
    logger.info("Step 1: Reading case_pack.csv (20 benchmark cases)...")
    cases = []
    with open(os.path.join(DATA_DIR, "case_pack.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)

    target_customers = {c["customer_id"] for c in cases}
    target_cards = {c["card_id"] for c in cases}
    flagged_txn_ids = {c["flagged_txn_id"] for c in cases}
    logger.info(f"Targeting {len(target_customers)} customers, {len(target_cards)} cards, {len(flagged_txn_ids)} flagged txns.")

    logger.info("Step 2: Reading closed_cases_history.csv (5,565 closed cases)...")
    closed_cases = []
    with open(os.path.join(DATA_DIR, "closed_cases_history.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            closed_cases.append(row)
    logger.info(f"Loaded {len(closed_cases)} historical closed cases.")

    logger.info("Step 3: Reading identity.csv...")
    identity_map = {}
    with open(os.path.join(DATA_DIR, "identity.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = row.get("TransactionID")
            if tid:
                identity_map[tid] = {
                    "DeviceType": row.get("DeviceType", ""),
                    "DeviceInfo": row.get("DeviceInfo", ""),
                    "id_15": row.get("id_15", ""),
                    "id_23": row.get("id_23", ""),
                    "id_30": row.get("id_30", ""),
                    "id_31": row.get("id_31", ""),
                    "id_33": row.get("id_33", ""),
                }
    logger.info(f"Loaded {len(identity_map)} identity profiles.")

    logger.info("Step 4: Streaming transactions.csv (708MB) to extract target customer records...")
    customer_txns: Dict[str, List[Dict[str, Any]]] = {c: [] for c in target_customers}
    all_matched_txns = {}

    with open(os.path.join(DATA_DIR, "transactions.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            count += 1
            cid = row.get("customer_id")
            tid = row.get("TransactionID")
            
            if cid in target_customers or tid in flagged_txn_ids:
                amt = float(row.get("TransactionAmt", 0.0))
                score = float(row.get("risk_score", 0.0)) if row.get("risk_score") else 0.0
                
                ident = identity_map.get(tid, {})
                device_profile = ""
                if ident.get("DeviceInfo"):
                    parts = [ident.get("DeviceInfo"), ident.get("id_30"), ident.get("id_31"), ident.get("id_33")]
                    device_profile = " | ".join([p for p in parts if p])

                txn_obj = {
                    "txn_id": tid,
                    "customer_id": cid,
                    "card_id": row.get("card1", ""),
                    "amount": amt,
                    "ts": row.get("ts", ""),
                    "channel": row.get("channel", ""),
                    "risk_score": score,
                    "product_cd": row.get("ProductCD", ""),
                    "addr1": row.get("addr1", ""),
                    "addr2": row.get("addr2", ""),
                    "p_emaildomain": row.get("P_emaildomain", ""),
                    "r_emaildomain": row.get("R_emaildomain", ""),
                    "device_profile": device_profile,
                    "is_new_device": ident.get("id_15") == "New",
                    "proxy_status": ident.get("id_23", ""),
                }
                
                if cid in customer_txns:
                    customer_txns[cid].append(txn_obj)
                all_matched_txns[tid] = txn_obj

            if count % 150000 == 0:
                logger.info(f"Processed {count:,} / 590,742 transactions...")

    logger.info(f"Stream complete. Total matched customer transactions: {sum(len(v) for v in customer_txns.values())}")

    staged_data = {
        "cases": cases,
        "closed_cases": closed_cases,
        "customer_txns": customer_txns,
        "all_matched_txns": all_matched_txns,
    }

    with open(OUTPUT_STAGED, "w", encoding="utf-8") as f:
        json.dump(staged_data, f, indent=2)

    logger.info(f"✅ Staged benchmark database successfully saved to: {OUTPUT_STAGED}")
    return staged_data


if __name__ == "__main__":
    run_indexing()
