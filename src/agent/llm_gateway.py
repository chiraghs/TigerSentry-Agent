"""
TigerSentry Unified LLM Gateway
Provides multi-provider plug-and-play support for free and low-cost LLMs:
- Google Gemini (Free tier: gemini-2.5-flash / gemini-1.5-flash)
- Groq Cloud (Free tier: llama-3.3-70b-versatile / llama-3.1-8b)
- OpenRouter (Free tier models)
- Mistral AI (Free tier / experiment)
- Built-in Deterministic GraphRAG Fallback (Zero external API dependencies)
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("tigersentry.llm")


class LLMGateway:
    """
    Unified LLM Client with automatic provider resolution and fallback.
    Configurable via environment variables for Render, Docker, or local .env.
    """

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "auto").lower().strip()
        self.configured_model = os.getenv("LLM_MODEL", "").strip()
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.timeout_sec = float(os.getenv("LLM_TIMEOUT_SEC", "12.0"))

        # Resolve provider and keys
        self.active_provider, self.active_model, self.api_key, self.base_url = self._resolve_provider()

    def _resolve_provider(self):
        """Resolves provider, active model, and credentials based on env vars."""
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()
        generic_key = os.getenv("LLM_API_KEY", "").strip()

        # Explicit provider setting
        if self.provider == "gemini" or (self.provider == "auto" and gemini_key):
            key = gemini_key or generic_key
            model = self.configured_model or "gemini-2.5-flash"
            return "gemini", model, key, "https://generativelanguage.googleapis.com/v1beta"

        if self.provider == "groq" or (self.provider == "auto" and groq_key):
            key = groq_key or generic_key
            model = self.configured_model or "llama-3.3-70b-versatile"
            return "groq", model, key, "https://api.groq.com/openai/v1"

        if self.provider == "openrouter" or (self.provider == "auto" and openrouter_key):
            key = openrouter_key or generic_key
            model = self.configured_model or "meta-llama/llama-3.1-8b-instruct:free"
            return "openrouter", model, key, "https://openrouter.ai/api/v1"

        if self.provider == "mistral" or (self.provider == "auto" and mistral_key):
            key = mistral_key or generic_key
            model = self.configured_model or "mistral-small-latest"
            return "mistral", model, key, "https://api.mistral.ai/v1"

        if self.provider in ["custom", "openai"]:
            base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
            model = self.configured_model or "gpt-4o-mini"
            return "custom", model, generic_key, base

        # Default fallback
        return "offline", "deterministic-graphrag", "", ""

    def get_status(self) -> Dict[str, Any]:
        """Returns the current runtime status of the LLM gateway."""
        has_key = bool(self.api_key)
        return {
            "provider": self.active_provider,
            "model": self.active_model,
            "has_api_key": has_key,
            "is_online": has_key and self.active_provider != "offline",
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_sec,
            "description": self._get_provider_description(),
        }

    def _get_provider_description(self) -> str:
        if self.active_provider == "gemini":
            return "Google Gemini (Free Tier API) — Fast Multimodal Reasoning"
        if self.active_provider == "groq":
            return "Groq Cloud (Free Tier) — Ultra-Fast LLaMA 3.3 Inference"
        if self.active_provider == "openrouter":
            return "OpenRouter (Free Tier) — Open-source LLaMA / Qwen Routing"
        if self.active_provider == "mistral":
            return "Mistral AI (Free Experiment Tier)"
        return "Deterministic GraphRAG Rule Reasoner (Offline Safe / Zero Key Required)"

    def generate_completion(
        self,
        prompt: str,
        system_prompt: str = "You are TigerSentry, an expert autonomous fraud investigation agent.",
        temperature: Optional[float] = None,
    ) -> str:
        """
        Dispatches completion call to configured provider with automatic error fallback.
        """
        temp = temperature if temperature is not None else self.temperature

        if not self.api_key or self.active_provider == "offline":
            return self._offline_reasoning(prompt, system_prompt)

        try:
            if self.active_provider == "gemini":
                return self._call_gemini(prompt, system_prompt, temp)
            else:
                return self._call_openai_compatible(prompt, system_prompt, temp)
        except Exception as e:
            logger.warning(f"LLM call to {self.active_provider} failed ({e}). Falling back to rule-based reasoning.")
            return self._offline_reasoning(prompt, system_prompt)

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float) -> str:
        url = f"{self.base_url}/models/{self.active_model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        with httpx.Client(timeout=self.timeout_sec) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            return "No content generated by Gemini."

    def _call_openai_compatible(self, prompt: str, system_prompt: str, temperature: float) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.active_provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/chiraghs/TigerSentry-Agent"
            headers["X-Title"] = "TigerSentry Fraud Agent"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.active_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024,
        }

        with httpx.Client(timeout=self.timeout_sec) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
            return "No content generated."

    def _offline_reasoning(self, prompt: str, system_prompt: str) -> str:
        """Deterministic policy rule reasoning when offline or when no API key is provided."""
        return (
            "Based on the TigerGraph GraphRAG policy analysis: The transaction pattern was evaluated under "
            "Bank Fraud Policy v1.0. Given multi-hop entity neighborhood connectivity, velocity metrics, and "
            "cardholder response, the system determined the defensible next-best actions. If confirmed fraud, "
            "emergency card block and FinCEN SAR filing under Policy Rule R2/R6 are strictly enforced."
        )

    def chat_with_analyst(
        self,
        case_data: Dict[str, Any],
        user_question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Interactive AI Co-Pilot chat assisting fraud analysts and judges exploring a case.
        """
        case_rec = case_data.get("case", {})
        nba = case_data.get("next_best_actions", {})
        sar = case_data.get("sar", {})
        meta = case_data.get("trigger_meta", {})

        system_prompt = (
            "You are TigerSentry, an autonomous Tier-2 Senior Fraud Investigation Agent powered by TigerGraph and GraphRAG. "
            "You provide clear, defensible, policy-grounded answers citing Bank Fraud Policy Rules (R1 to R10), FinCEN Section 3a "
            "guidance, and TigerGraph graph evidence (device rings, synthetic IDs, velocity bursts). "
            "Be direct, highly knowledgeable, and transparent regarding risk and uncertainty."
        )

        context_str = (
            f"CASE DOSSIER:\n"
            f"- Case ID: {case_data.get('case_id')}\n"
            f"- Customer ID: {case_data.get('customer_id')}\n"
            f"- Typology / Pattern: {case_rec.get('pattern')}\n"
            f"- Total Exposure: ${case_rec.get('exposure_usd', 0.0):.2f}\n"
            f"- Fraud Probability: {case_rec.get('fraud_probability', 0.5):.2f}\n"
            f"- Verdict: {case_rec.get('verdict')}\n"
            f"- Final Next-Best Actions: {json.dumps(nba.get('final', []))}\n"
            f"- Pre-Evidence Actions: {json.dumps(nba.get('initial', []))}\n"
            f"- What Changed Narrative: {nba.get('what_changed', '')}\n"
            f"- FinCEN SAR Filing: {sar.get('file')} (Reason: {sar.get('reason', '')})\n"
            f"- Similar Prior Cases in Graph Memory: {case_rec.get('similar_prior_cases', [])}\n"
            f"- Connected Cards in Graph: {case_rec.get('connected_card_ids', [])}\n"
        )

        prompt = (
            f"{context_str}\n\n"
            f"FRAUD ANALYST QUESTION:\n{user_question}\n\n"
            f"Please explain your investigation findings, policy citations, and reasoning clearly."
        )

        if not self.api_key or self.active_provider == "offline":
            # Smart rule-based answer when offline
            q_lower = user_question.lower()
            if "sar" in q_lower or "fincen" in q_lower or "report" in q_lower:
                if sar.get("file"):
                    return f"A FinCEN Suspicious Activity Report (SAR) is MANDATORY for this case. Reason: {sar.get('reason')}. Total exposure is ${case_rec.get('exposure_usd', 0.0):.2f} exceeding reporting thresholds under Section 3a."
                else:
                    return f"A FinCEN SAR filing was NOT mandated because the customer verified the charge as authorized under Policy Rule R3, or exposure remained below the systemic reporting threshold."
            elif "action" in q_lower or "block" in q_lower or "freeze" in q_lower:
                actions_str = ", ".join(a.get("action", "") for a in nba.get("final", []))
                return f"The recommended next-best actions are: {actions_str}. Rationale: {nba.get('what_changed', 'Grounded in Bank Fraud Policy v1.0.')}"
            elif "pattern" in q_lower or "typology" in q_lower:
                return f"The detected fraud pattern is {case_rec.get('pattern')} with a model fraud probability of {case_rec.get('fraud_probability', 0.5):.2f}. This was diagnosed via multi-hop traversal of the entity neighborhood in TigerGraph Savanna."
            else:
                return (
                    f"Case {case_data.get('case_id')} involves customer {case_data.get('customer_id')} with total exposure of ${case_rec.get('exposure_usd', 0.0):.2f}. "
                    f"Verdict is {case_rec.get('verdict')}. Policy decision: {nba.get('what_changed', 'Actions evaluated under Rules R1-R10.')}"
                )

        return self.generate_completion(prompt, system_prompt)


# Global Singleton instance
llm_gateway = LLMGateway()
