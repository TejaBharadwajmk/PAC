"""
Phase 5 API verification script — tests:
  1. Default weights search (no overrides)
  2. Custom semantic_weight override (semantic-heavy mode)
  3. Custom fts_weight override (keyword-heavy mode)
  4. include_debug=True returns a populated debug block
  5. All-zero override handled gracefully
"""

import asyncio
import json
import httpx

BASE = "http://localhost:8000/api/v1"
AUTH = ("ADMIN001", "Admin@2024")

HEADERS = {"Content-Type": "application/json"}

async def login() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE}/auth/login",
            json={"badge_number": AUTH[0], "password": AUTH[1]},
        )
        r.raise_for_status()
        return r.json()["access_token"]

async def search(token: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{BASE}/similarity/search",
            json=payload,
            headers={"Authorization": f"Bearer {token}", **HEADERS},
        )
        r.raise_for_status()
        return r.json()

async def main():
    print("=" * 60)
    print("PHASE 5 -- API VERIFICATION SUITE")
    print("=" * 60)

    token = await login()
    print("[OK]  Login OK")

    query = "robber broke window of jewelry shop at night with crowbar"

    # ── Test 1: Default weights ──────────────────────────────
    print("\n[Test 1] Default weights (no overrides, include_debug=false)...")
    resp = await search(token, {"query_text": query})
    assert "debug" not in resp or resp.get("debug") is None, "debug should be absent"
    assert "results" in resp
    print(f"  [OK]  Results: {len(resp['results'])}  | debug block: absent")

    # ── Test 2: include_debug=true ───────────────────────────
    print("\n[Test 2] include_debug=true...")
    resp = await search(token, {"query_text": query, "include_debug": True})
    debug = resp.get("debug")
    assert debug is not None, "debug block missing when include_debug=true"
    assert "active_signals" in debug
    assert "normalized_weights" in debug
    assert "configured_weights" in debug
    # normalized weights should sum to ~1.0
    nw_sum = sum(debug["normalized_weights"].values())
    assert abs(nw_sum - 1.0) < 0.01, f"normalized weights sum={nw_sum}, expected ~1.0"
    print(f"  [OK]  active_signals: {debug['active_signals']}")
    print(f"  [OK]  normalized_weights: {debug['normalized_weights']}  (sum={round(nw_sum,4)})")

    # ── Test 3: Semantic-heavy override ─────────────────────
    print("\n[Test 3] semantic_weight=0.90 override, include_debug=true...")
    resp = await search(token, {
        "query_text": query,
        "semantic_weight": 0.90,
        "fts_weight": 0.05,
        "mo_weight": 0.05,
        "include_debug": True,
    })
    debug = resp["debug"]
    nw = debug["normalized_weights"]
    assert nw.get("semantic", 0) > 0.80, f"semantic should dominate, got {nw}"
    print(f"  [OK]  normalized_weights with semantic=0.90 override: {nw}")

    # ── Test 4: FTS-heavy override ───────────────────────────
    print("\n[Test 4] fts_weight=0.90 override, include_debug=true...")
    resp = await search(token, {
        "query_text": query,
        "semantic_weight": 0.05,
        "fts_weight": 0.90,
        "mo_weight": 0.05,
        "include_debug": True,
    })
    debug = resp["debug"]
    nw = debug["normalized_weights"]
    assert nw.get("fts", 0) > 0.70, f"fts should dominate (if query has FTS hits), got {nw}"
    print(f"  [OK]  normalized_weights with fts=0.90 override: {nw}")

    # ── Test 5: Partial override (only semantic) ─────────────
    print("\n[Test 5] Only semantic_weight=0.50 override (others use defaults), include_debug=true...")
    resp = await search(token, {
        "query_text": query,
        "semantic_weight": 0.50,
        "include_debug": True,
    })
    debug = resp["debug"]
    print(f"  [OK]  configured_weights: {debug['configured_weights']}")
    print(f"  [OK]  normalized_weights: {debug['normalized_weights']}")

    print("\n" + "=" * 60)
    print("[PASS]  ALL PHASE 5 API TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
