"""
Unit and integration tests for TigerSentry LLM Gateway and AI Co-Pilot chat.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.agent.llm_gateway import LLMGateway
from src.api.server import app


def test_llm_gateway_offline_default():
    """Verifies gateway initializes safely when no API keys are present."""
    with patch.dict(os.environ, {}, clear=True):
        gw = LLMGateway()
        status = gw.get_status()
        assert status["provider"] == "offline"
        assert status["model"] == "deterministic-graphrag"
        assert status["has_api_key"] is False
        assert status["is_online"] is False


def test_llm_gateway_gemini_routing():
    """Verifies automatic detection and routing to Google Gemini."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyFakeKey123", "LLM_PROVIDER": "auto"}):
        gw = LLMGateway()
        status = gw.get_status()
        assert status["provider"] == "gemini"
        assert "gemini" in status["model"]
        assert status["has_api_key"] is True
        assert status["is_online"] is True


def test_llm_gateway_groq_routing():
    """Verifies automatic detection and routing to Groq Cloud."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_fakeKey123", "LLM_PROVIDER": "groq"}):
        gw = LLMGateway()
        status = gw.get_status()
        assert status["provider"] == "groq"
        assert "llama" in status["model"]
        assert status["has_api_key"] is True
        assert status["is_online"] is True


def test_llm_gateway_openrouter_routing():
    """Verifies automatic detection and routing to OpenRouter."""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-fake123", "LLM_PROVIDER": "openrouter"}):
        gw = LLMGateway()
        status = gw.get_status()
        assert status["provider"] == "openrouter"
        assert status["has_api_key"] is True


def test_llm_gateway_offline_chat():
    """Verifies offline policy reasoning provides defensible answers."""
    gw = LLMGateway()
    case_data = {
        "case_id": "HHG-001",
        "customer_id": "C12382",
        "case": {
            "pattern": "OUT_OF_REGION_USE",
            "exposure_usd": 77.07,
            "fraud_probability": 0.68,
            "verdict": "fraud",
        },
        "next_best_actions": {
            "final": [{"action": "BLOCK_CARD", "route": "L1", "reason": "R2 unauthorized"}]
        },
        "sar": {"file": True, "reason": "R2 confirmed unauthorized use"},
    }
    
    # Test SAR question
    sar_reply = gw.chat_with_analyst(case_data, "Why is a FinCEN SAR filing required?")
    assert "SAR" in sar_reply
    assert "MANDATORY" in sar_reply
    assert "$77.07" in sar_reply

    # Test actions question
    act_reply = gw.chat_with_analyst(case_data, "What action did you take?")
    assert "BLOCK_CARD" in act_reply


def test_api_llm_status_and_chat():
    """Verifies the FastAPI LLM status and AI chat endpoints."""
    client = TestClient(app)
    
    # Status endpoint
    s_resp = client.get("/api/v1/llm/status")
    assert s_resp.status_code == 200
    s_data = s_resp.json()
    assert "provider" in s_data
    assert "model" in s_data
    assert "is_online" in s_data

    # Chat endpoint
    c_resp = client.post("/api/v1/agent/chat", json={
        "case_id": "HHG-001",
        "question": "Explain the fraud pattern and risk score."
    })
    assert c_resp.status_code == 200
    c_data = c_resp.json()
    assert c_data["case_id"] == "HHG-001"
    assert len(c_data["response"]) > 0
    assert "llm_provider" in c_data
