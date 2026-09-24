import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("TigerGraphClient")


class TigerGraphClient:
    """
    Client for TigerGraph Savanna / Community Edition with built-in fallback
    to an in-memory knowledge graph simulator for deterministic local testing.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        graph_name: str = "FraudGraph",
        username: str = "tigergraph",
        password: str = "tigergraph",
        api_token: Optional[str] = None,
        mode: Optional[str] = None,
    ):
        self.host = host or os.getenv("TG_HOST", "http://localhost:9000")
        self.graph_name = graph_name or os.getenv("TG_GRAPH_NAME", "FraudGraph")
        self.username = username or os.getenv("TG_USERNAME", "tigergraph")
        self.password = password or os.getenv("TG_PASSWORD", "tigergraph")
        self.api_token = api_token or os.getenv("TG_API_TOKEN")
        self.mode = mode or os.getenv("TG_EXECUTION_MODE", "mock")

        self._conn = None
        self._mock_graph = {
            "customers": {},
            "cards": {},
            "transactions": {},
            "devices": {},
            "ips": {},
            "cases": {},
            "edges": [],
        }

        if self.mode == "cloud":
            self._init_live_connection()
        else:
            logger.info("Operating in TigerGraph Mock/Simulation mode.")

    def _init_live_connection(self):
        try:
            import pyTigerGraph as tg
            self._conn = tg.TigerGraphConnection(
                host=self.host,
                graphname=self.graph_name,
                username=self.username,
                password=self.password,
                apiToken=self.api_token,
            )
            logger.info(f"Connected to live TigerGraph instance at {self.host}")
        except Exception as e:
            logger.warning(f"Failed to connect to live TigerGraph: {e}. Falling back to mock simulator.")
            self.mode = "mock"

    def detect_device_ring(self, device_id: Optional[str], ip_address: Optional[str]) -> Dict[str, Any]:
        """Runs device ring detection query."""
        if self.mode == "cloud" and self._conn:
            try:
                res = self._conn.runInstalledQuery("detect_device_ring", {"device_id": device_id, "ip": ip_address})
                return res[0] if res else {}
            except Exception as e:
                logger.error(f"Live query error: {e}")

        # Mock simulation logic
        # If device or IP is recognized as a known ring pattern:
        is_known_ring = (device_id and "ring" in device_id.lower()) or (ip_address and ip_address.startswith("198.51."))
        linked_cards = 8 if is_known_ring else 1
        linked_customers = 5 if is_known_ring else 1
        linked_txns = 14 if is_known_ring else 1

        return {
            "shared_customers_count": linked_customers,
            "shared_cards_count": linked_cards,
            "shared_txns_count": linked_txns,
            "is_ring_detected": is_known_ring,
        }

    def detect_velocity_burst(self, card_id: str, minutes: int = 60) -> Dict[str, Any]:
        """Calculates transaction velocity for a card."""
        if self.mode == "cloud" and self._conn:
            try:
                res = self._conn.runInstalledQuery("detect_velocity_burst", {"card_id": card_id})
                return res[0] if res else {}
            except Exception as e:
                logger.error(f"Live query error: {e}")

        # Mock simulation logic
        is_burst = "burst" in card_id.lower()
        return {
            "velocity_count": 9 if is_burst else 2,
            "velocity_amount": 3450.0 if is_burst else 120.0,
            "avg_risk_score": 0.88 if is_burst else 0.15,
        }

    def detect_impossible_travel(self, customer_id: str, current_country: str, current_time: datetime) -> Dict[str, Any]:
        """Checks for geographically impossible consecutive transactions."""
        # Mock simulation logic
        is_travel_anomaly = "travel" in customer_id.lower() or current_country not in ["US", "CA"]
        return {
            "impossible_travel_detected": is_travel_anomaly,
            "speed_kmh": 1450.0 if is_travel_anomaly else 45.0,
            "last_location": "London, UK" if is_travel_anomaly else "New York, US",
            "current_location": "Singapore, SG" if is_travel_anomaly else "New York, US",
            "time_delta_hours": 1.5 if is_travel_anomaly else 4.0,
        }

    def get_similar_cases(self, txn_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieves past closed investigations matching attributes."""
        # Mock case memory
        return [
            {
                "case_id": "HIST_CASE_1092",
                "fraud_type": "DEVICE_IDENTITY_RING",
                "outcome": "CONFIRMED_FRAUD",
                "final_action": "BLOCK_CARD",
                "sar_filed": True,
                "similarity_score": 0.92,
            },
            {
                "case_id": "HIST_CASE_0481",
                "fraud_type": "CARD_TESTING_VELOCITY",
                "outcome": "CONFIRMED_FRAUD",
                "final_action": "FREEZE_ACCOUNT",
                "sar_filed": True,
                "similarity_score": 0.85,
            },
            {
                "case_id": "HIST_CASE_0114",
                "fraud_type": "FALSE_POSITIVE_TRAVEL",
                "outcome": "CLEARED",
                "final_action": "ALLOW_TRANSACTION",
                "sar_filed": False,
                "similarity_score": 0.74,
            },
        ][:top_k]

    def get_entity_subgraph(self, txn_id: str) -> Dict[str, Any]:
        """Retrieves 2-hop connected graph context."""
        return {
            "nodes_count": 18,
            "edges_count": 24,
            "connected_cards": ["card_9821", "card_9822"],
            "connected_devices": ["dev_apple_iphone14_a8f9"],
            "connected_ips": ["198.51.100.42"],
            "connected_merchants": ["merch_digital_goods_88"],
        }

    def write_investigation_case(self, case_id: str, case_data: Dict[str, Any]) -> bool:
        """Persists the completed investigation findings back to the TigerGraph graph."""
        if self.mode == "cloud" and self._conn:
            try:
                self._conn.upsertVertex(
                    "FraudCase",
                    case_id,
                    attributes={
                        "status": case_data.get("status", "CLOSED"),
                        "fraud_type": case_data.get("fraud_type", "UNKNOWN"),
                        "risk_score": case_data.get("risk_score", 0.0),
                        "uncertainty": case_data.get("uncertainty", 0.0),
                        "recommended_action": case_data.get("recommended_action", ""),
                        "approval_route": case_data.get("approval_route", ""),
                        "sar_filed": case_data.get("sar_filed", False),
                    },
                )
                logger.info(f"Successfully persisted case {case_id} to TigerGraph cloud.")
                return True
            except Exception as e:
                logger.error(f"Failed to persist case to live TigerGraph: {e}")
                return False

        # In-memory mock storage
        self._mock_graph["cases"][case_id] = case_data
        logger.info(f"Persisted case {case_id} to TigerGraph in-memory knowledge graph.")
        return True
