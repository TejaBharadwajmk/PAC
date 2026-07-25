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
        full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"
        try:
            # Gemini SDK generate_content is synchronous but fast enough
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._model.generate_content(full_prompt),
            )
            return response.text or ""
        except Exception as exc:
            logger.error(f"Gemini generation failed: {exc}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Verify API key and model accessibility."""
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
        self._timeout = getattr(settings, "OLLAMA_TIMEOUT", 60.0)
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
                    return msg.get("content", "")
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
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except Exception as exc:
            logger.error(f"Ollama generation failed: {exc}")
            raise RuntimeError(
                f"Air-gapped Ollama local LLM service error ({self._base_url}): {exc}"
            ) from exc

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


# ── Mock Provider (Tests) ──────────────────────────────────────────────────────

class MockProvider(BaseLLM):
    """Deterministic stub for unit tests.  Never makes network calls."""

    RESPONSE_TEMPLATE = (
        "Based on the provided PAC intelligence data, the analysis indicates "
        "a HIGH risk profile. The criminal has committed 9 chain snatching crimes "
        "with 87% occurring between 19:00-22:00. Operating radius is 3.2 km. "
        "Association strength with co-offenders is elevated. "
        "Recommended action: Increase patrol coverage in identified hotspot zones "
        "during evening hours."
    )

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        logger.debug("MockProvider.generate called (test mode)")
        return self.RESPONSE_TEMPLATE

    async def health_check(self) -> Dict[str, Any]:
        return {"provider": "mock", "status": "healthy", "model": "mock-v1"}


# ── Factory ────────────────────────────────────────────────────────────────────

def get_llm_provider() -> BaseLLM:
    """Factory that returns the configured LLM provider singleton.

    Controlled by the LLM_PROVIDER environment variable:
      gemini  → GeminiProvider  (default)
      ollama  → OllamaProvider
      mock    → MockProvider
    """
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini":
        return GeminiProvider()
    elif provider == "ollama":
        return OllamaProvider()
    elif provider == "mock":
        return MockProvider()
    else:
        logger.warning(
            f"Unknown LLM_PROVIDER='{provider}'. Falling back to MockProvider."
        )
        return MockProvider()
