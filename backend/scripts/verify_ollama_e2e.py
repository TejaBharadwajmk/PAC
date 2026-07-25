"""
End-to-End Real Prompt Verification for Ollama Local LLM.

Tests:
  1. Confirm Ollama container is healthy (GET /api/tags)
  2. Confirm downloaded models are present
  3. Send real prompt to Ollama and verify end-to-end generated response
"""

import asyncio
import httpx
from app.services.llm_provider import OllamaProvider
from app.config import settings

async def main():
    print("=" * 60)
    print("OLLAMA REAL PROMPT END-TO-END VERIFICATION")
    print("=" * 60)

    ollama_url = settings.OLLAMA_URL.rstrip("/")
    # 1. Health check & tags
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{ollama_url}/api/tags")
        assert r.status_code == 200
        tags = r.json()
        models = [m["name"] for m in tags.get("models", [])]
        print(f"\n[1] Ollama Container Health ({ollama_url}): HEALTHY")
        print(f"[2] Downloaded Models in Ollama: {models}")

    assert len(models) > 0, "No models downloaded in Ollama"
    target_model = models[0]  # e.g., 'smollm:135m' or 'mistral:latest'

    # Override settings to point to the downloaded test model
    settings.OLLAMA_MODEL = target_model

    # 3. Real Prompt Generation via OllamaProvider
    print(f"\n[3] Sending REAL End-to-End Prompt to model '{target_model}'...")
    provider = OllamaProvider()

    system_prompt = "You are a Karnataka State Police investigation AI assistant."
    user_message = "Summarize crime trend for chain snatching in Bengaluru."

    start_t = asyncio.get_event_loop().time()
    response_text = await provider.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=100,
    )
    elapsed = asyncio.get_event_loop().time() - start_t

    print("\n--- REAL LLM OUTPUT ---")
    print(response_text.strip())
    print("------------------------")
    print(f"  [OK] Generated {len(response_text)} chars in {round(elapsed, 2)}s")
    assert len(response_text.strip()) > 0, "LLM returned empty response"

    print("\n" + "=" * 60)
    print("[PASS] REAL PROMPT END-TO-END VERIFICATION SUCCESSFUL!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
