"""
B2 Local LLM & Air-Gapped Intelligence — Verification Script.

Tests:
  1. MockProvider generation & health check
  2. OllamaProvider initialization & air-gapped health check
  3. GeminiProvider initialization & health check
  4. Factory switching via get_llm_provider()
  5. API Integration: /api/v1/assistant/health endpoint verification
"""

import asyncio
import httpx
from app.services.llm_provider import (
    BaseLLM,
    MockProvider,
    OllamaProvider,
    GeminiProvider,
    get_llm_provider,
)
from app.config import settings

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_BADGE = "ADMIN001"
ADMIN_PASS = "Admin@2024"


async def login() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}/auth/login",
            json={"badge_number": ADMIN_BADGE, "password": ADMIN_PASS},
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def main():
    print("=" * 60)
    print("B2 -- AIR-GAPPED LOCAL LLM VERIFICATION SUITE")
    print("=" * 60)

    # ── Test 1: MockProvider ───────────────────────────────────
    print("\n[Test 1] Testing MockProvider...")
    mock = MockProvider()
    mock_health = await mock.health_check()
    assert mock_health["status"] == "healthy"
    assert mock_health["provider"] == "mock"

    mock_resp = await mock.generate(
        system_prompt="You are a KSP investigation assistant.",
        user_message="Summarize risk profile for suspect.",
    )
    assert "HIGH risk profile" in mock_resp
    print("  [OK]  MockProvider generated expected test text")
    print(f"  [OK]  Health check: {mock_health}")

    # ── Test 2: OllamaProvider ─────────────────────────────────
    print("\n[Test 2] Testing OllamaProvider (Air-Gapped Local LLM)...")
    ollama = OllamaProvider()
    ollama_health = await ollama.health_check()
    assert "provider" in ollama_health and ollama_health["provider"] == "ollama"
    assert "air_gapped" in ollama_health and ollama_health["air_gapped"] is True
    print(f"  [OK]  OllamaProvider initialized successfully")
    print(f"  [OK]  Ollama status: {ollama_health['status']} | Model: {ollama_health['model']}")

    # ── Test 3: GeminiProvider ─────────────────────────────────
    print("\n[Test 3] Testing GeminiProvider structure...")
    try:
        gemini = GeminiProvider()
        gemini_health = await gemini.health_check()
        print(f"  [OK]  GeminiProvider status: {gemini_health['status']}")
    except Exception as exc:
        print(f"  [INFO] GeminiProvider not active / key missing: {exc}")

    # ── Test 4: Factory Switching ──────────────────────────────
    print("\n[Test 4] Testing get_llm_provider() factory switching...")
    orig_provider = settings.LLM_PROVIDER
    
    settings.LLM_PROVIDER = "mock"
    p_mock = get_llm_provider()
    assert isinstance(p_mock, MockProvider)
    print("  [OK]  LLM_PROVIDER='mock' -> MockProvider")

    settings.LLM_PROVIDER = "ollama"
    p_ollama = get_llm_provider()
    assert isinstance(p_ollama, OllamaProvider)
    print("  [OK]  LLM_PROVIDER='ollama' -> OllamaProvider")

    settings.LLM_PROVIDER = orig_provider
    print(f"  [OK]  Restored default LLM_PROVIDER='{orig_provider}'")

    # ── Test 5: API Health Endpoint Integration ───────────────
    print("\n[Test 5] GET /api/v1/assistant/health...")
    token = await login()
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BASE_URL}/assistant/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        data = res.json()
        assert "provider" in data
        assert "supported_intents" in data
        print(f"  [OK]  API health check response: provider={data['provider']}, status={data['status']}")
        print(f"  [OK]  Available modules: {len(data['available_modules'])} | Supported intents: {len(data['supported_intents'])}")

    print("\n" + "=" * 60)
    print("[PASS]  ALL B2 LOCAL LLM TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
