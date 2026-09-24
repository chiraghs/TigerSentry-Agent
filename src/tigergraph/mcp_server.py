"""
TigerGraph MCP Protocol Adapter
Exposes TigerGraph graph capabilities and GSQL queries as agent-executable tools
aligned with the official tigergraph-mcp tool contracts.
"""

from typing import Dict, Any, List, Optional
from src.tigergraph.client import TigerGraphClient


class TigerGraphMCPServer:
    def __init__(self, tg_client: Optional[TigerGraphClient] = None):
        self.client = tg_client or TigerGraphClient()

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Returns schemas of available tools exposed via MCP."""
        return [
            {
                "name": "tg_detect_device_ring",
                "description": "Traverses the graph to detect if device/IP is shared by multiple cards/identities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string"},
                        "ip_address": {"type": "string"},
                    },
                },
            },
            {
                "name": "tg_detect_velocity_burst",
                "description": "Calculates card transaction velocity and sum in recent rolling windows.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_id": {"type": "string"},
                        "minutes": {"type": "integer", "default": 60},
                    },
                    "required": ["card_id"],
                },
            },
            {
                "name": "tg_detect_impossible_travel",
                "description": "Calculates speed and distance between consecutive transactions across geolocations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "country": {"type": "string"},
                    },
                    "required": ["customer_id"],
                },
            },
            {
                "name": "tg_get_subgraph",
                "description": "Fetches the 2-hop connected neighborhood of a transaction for GraphRAG.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "txn_id": {"type": "string"},
                    },
                    "required": ["txn_id"],
                },
            },
            {
                "name": "tg_get_similar_cases",
                "description": "Searches case memory for past closed cases with shared graph topologies.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "txn_id": {"type": "string"},
                        "top_k": {"type": "integer", "default": 3},
                    },
                    "required": ["txn_id"],
                },
            },
        ]

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an MCP tool call to the corresponding TigerGraph GSQL operation."""
        if tool_name == "tg_detect_device_ring":
            return self.client.detect_device_ring(
                device_id=arguments.get("device_id"),
                ip_address=arguments.get("ip_address"),
            )
        elif tool_name == "tg_detect_velocity_burst":
            return self.client.detect_velocity_burst(
                card_id=arguments["card_id"],
                minutes=arguments.get("minutes", 60),
            )
        elif tool_name == "tg_detect_impossible_travel":
            from datetime import datetime
            return self.client.detect_impossible_travel(
                customer_id=arguments["customer_id"],
                current_country=arguments.get("country", "US"),
                current_time=datetime.utcnow(),
            )
        elif tool_name == "tg_get_subgraph":
            return self.client.get_entity_subgraph(
                txn_id=arguments["txn_id"],
            )
        elif tool_name == "tg_get_similar_cases":
            return {"similar_cases": self.client.get_similar_cases(
                txn_id=arguments["txn_id"],
                top_k=arguments.get("top_k", 3),
            )}
        else:
            raise ValueError(f"Unknown TigerGraph MCP tool: {tool_name}")
