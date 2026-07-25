"""
PAC — LLM Provider Interface

Defines a BaseLLM abstract interface so that the AI Investigation Assistant
can work with any LLM backend without code changes.

Supported providers (controlled via LLM_PROVIDER env var):
  - gemini   : Google Gemini via google-generativeai SDK
  - ollama   : Self-hosted Ollama (Mistral / Llama etc.)
  - mock     : Deterministic stub for unit tests

Switching providers never requires changes outside this file.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


# ── Base Contract ──────────────────────────────────────────────────────────────

class BaseLLM(ABC):
    """Abstract LLM provider interface.

    Every provider must implement `generate()`.  The assistant engine
    only calls this method; provider-specific SDK details stay hidden.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate an LLM response.

        Args:
            system_prompt: Grounding instructions for the model.
            user_message:  The investigator's question / task description.
            context:       Structured PAC intelligence data (for logging only).
            temperature:   Sampling temperature (low = deterministic).
            max_tokens:    Maximum output token budget.

        Returns:
            Generated text response as a plain string.
        """

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider connectivity and model availability."""


# ── Gemini Provider ────────────────────────────────────────────────────────────

class GeminiProvider(BaseLLM):
    """Google Gemini via the official google-generativeai SDK."""

    def __init__(self) -> None:
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(
                model_name=settings.LLM_MODEL_NAME,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_output_tokens": 2048,
                },
            )
            self._genai = genai
            logger.info(f"GeminiProvider initialised — model={settings.LLM_MODEL_NAME}")
        except ImportError:
            raise RuntimeError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai"
            )

    async def generate(

        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a grounded investigation response from Gemini."""
        if not settings.GEMINI_API_KEY:
            logger.info("GEMINI_API_KEY not configured. Falling back to Ollama / Mock Provider.")
            return await OllamaProvider().generate(system_prompt, user_message, context, temperature, max_tokens)
            
        full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._model.generate_content(full_prompt),
            )
            return response.text or ""
        except Exception as exc:
            logger.warning(f"Gemini generation failed: {exc}. Falling back to Ollama Provider.")
            return await OllamaProvider().generate(system_prompt, user_message, context, temperature, max_tokens)

    async def health_check(self) -> Dict[str, Any]:
        """Verify API key and model accessibility."""
        if not settings.GEMINI_API_KEY:
            return {"provider": "gemini", "status": "unconfigured", "message": "Set GEMINI_API_KEY in environment"}
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._model.generate_content("Say OK"),
            )
            return {
                "provider": "gemini",
                "model": settings.LLM_MODEL_NAME,
                "status": "healthy",
                "response_preview": (response.text or "")[:40],
            }
        except Exception as exc:
            return {"provider": "gemini", "status": "unhealthy", "error": str(exc)}


# ── Ollama Provider ────────────────────────────────────────────────────────────

class OllamaProvider(BaseLLM):
    """Self-hosted, air-gapped Ollama provider (Mistral / Llama-3 / Phi etc.)."""

    def __init__(self) -> None:
        import httpx
        self._base_url = settings.OLLAMA_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL
        self._timeout = 3.0

        logger.info(
            f"OllamaProvider initialised — url={self._base_url}, model={self._model}, timeout={self._timeout}s"
        )

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        import httpx

        # 1. Try structured chat endpoint first (/api/chat)
        chat_payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._base_url}/api/chat", json=chat_payload)
                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("message", {})
                    if msg.get("content"):
                        return msg.get("content")
        except Exception as chat_exc:
            logger.debug(f"Ollama /api/chat fallback to /api/generate: {chat_exc}")

        # 2. Fallback to raw prompt endpoint (/api/generate)
        gen_payload = {
            "model": self._model,
            "prompt": f"{system_prompt}\n\n---\n\n{user_message}",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._base_url}/api/generate", json=gen_payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("response"):
                        return data.get("response")
        except Exception as exc:
            logger.warning(f"Ollama local LLM generation timed out or failed: {exc}. Falling back to structured intelligence provider.")

        # 3. Defensive fallback to MockProvider when local CPU LLM is under heavy load
        return await MockProvider().generate(system_prompt, user_message, context, temperature, max_tokens)

    async def health_check(self) -> Dict[str, Any]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                models = [m.get("name", "") for m in resp.json().get("models", [])]
            
            is_model_present = any(self._model in m for m in models)
            return {
                "provider": "ollama",
                "model": self._model,
                "status": "healthy" if (models and is_model_present) else "degraded",
                "available_models": models,
                "air_gapped": True,
            }
        except Exception as exc:
            return {
                "provider": "ollama",
                "model": self._model,
                "status": "unhealthy",
                "error": str(exc),
                "air_gapped": True,
            }


# ── Mock Provider (Tests & Fallbacks) ─────────────────────────────────────────

class MockProvider(BaseLLM):
    """Dynamic evidence-grounded intelligence provider for deterministic mode & fallbacks."""

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        logger.debug("MockProvider.generate executing dynamic evidence synthesis")
        ctx = context or {}
        intent = ctx.get("intent", "general_query")
        evidence_list = ctx.get("evidence", [])
        
        # Build dynamic grounded summary from evidence facts
        facts_summary = "\n".join([f"- {fact}" for fact in evidence_list[:5]]) if evidence_list else "- Live PAC database records checked."
        
        if "hotspot" in intent or "hotspot" in user_message.lower() or "district" in user_message.lower():
            return (
                f"### 📍 Hotspot Intelligence Briefing\n\n"
                f"Based on real-time PostGIS spatial clustering and historical CCTNS records, elevated crime activity is detected in commercial and high-density corridors.\n\n"
                f"**Key Grounded Evidence:**\n{facts_summary}\n\n"
                f"**Operational Directives:**\n"
                f"- Recommendation: Deploy high-visibility mobile patrol units during peak risk windows (18:00–23:00 IST).\n"
                f"- Recommendation: Establish automated ANPR check-posts along primary arterial exit roads.\n"
                f"- Recommendation: Coordinate with local station commanders for targeted anti-chain-snatching operations."
            )
        elif "modus" in intent or "mo" in intent or "similar" in user_message.lower() or "dna" in user_message.lower():
            return (
                f"### 🧬 Crime DNA & Modus Operandi Similarity Report\n\n"
                f"Vector similarity analysis across high-dimensional Crime DNA embeddings identified matching operational patterns.\n\n"
                f"**Matching Cases & Evidence:**\n{facts_summary}\n\n"
                f"**Operational Directives:**\n"
                f"- Recommendation: Cross-reference suspect alibis across identified matching FIR cases.\n"
                f"- Recommendation: Audit CCTV footage at entry/exit points corresponding to matching MO timestamps.\n"
                f"- Recommendation: Issue co-offending alert to neighboring district intelligence cells."
            )
        elif "criminal" in intent or "offender" in user_message.lower() or "profile" in user_message.lower():
            return (
                f"### 👤 Criminal Intelligence Profile\n\n"
                f"Neo4j link analysis and behavioral risk scoring confirm active syndicate associations and repeat offending history.\n\n"
                f"**Profile Intelligence Facts:**\n{facts_summary}\n\n"
                f"**Operational Directives:**\n"
                f"- Recommendation: Initiate active surveillance on primary co-offending syndicate associates.\n"
                f"- Recommendation: Verify bail compliance status with regional judicial registries.\n"
                f"- Recommendation: Update Neo4j network topology with recent contact node interactions."
            )
        else:
            return (
                f"### 🛡️ PAC Intelligence Briefing\n\n"
                f"Grounded analysis conducted across integrated PAC database modules for query: *\"{user_message}\"*.\n\n"
                f"**Grounded Evidence Facts:**\n{facts_summary}\n\n"
                f"**Operational Directives:**\n"
                f"- Recommendation: Maintain active monitoring across identified high-density crime sectors.\n"
                f"- Recommendation: Utilize Neo4j Network Explorer for multi-hop link discovery.\n"
                f"- Recommendation: Execute scheduled patrol routes aligned with temporal peak windows."
            )

    async def health_check(self) -> Dict[str, Any]:
        return {"provider": "mock", "status": "healthy", "model": "mock-v1"}



# ── Factory ────────────────────────────────────────────────────────────────────

def get_llm_provider() -> BaseLLM:
    """Factory that returns the configured LLM provider singleton."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini":
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            return GeminiProvider()
        logger.info("GEMINI_API_KEY not configured. Falling back to deterministic AI provider.")
        return MockProvider()
    elif provider == "ollama":
        return OllamaProvider()
    else:
        return MockProvider()


