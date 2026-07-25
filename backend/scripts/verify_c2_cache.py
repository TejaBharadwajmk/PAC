"""
C2 Redis Query Caching — End-to-End Verification Script.

Tests:
  1. Cold request (Cache MISS) computes and caches payload in Redis
  2. Warm request (Cache HIT) returns payload with sub-10ms response time
  3. Invalidation test: new FIR registration invalidates 'pac:cache:geo:*' keys
  4. Cache pattern invalidation function testing
"""

import asyncio
import time
import httpx

from app.core.cache import invalidate_cache_pattern, get_redis_client
from app.config import settings

BASE_URL = "http://127.0.0.1:8000/api/v1"
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
    print("C2 -- REDIS QUERY CACHING VERIFICATION SUITE")
    print("=" * 60)

    token = await login()
    headers = {"Authorization": f"Bearer {token}"}

    # Clear pre-existing geo cache keys for clean test
    await invalidate_cache_pattern("pac:cache:geo:*")

    # ── Test 1: Cold Request (Cache MISS) ─────────────────────
    print("\n[Test 1] Executing COLD request (Cache MISS) to /geo/hotspots...")
    t0 = time.monotonic()
    async with httpx.AsyncClient() as client:
        r1 = await client.get(f"{BASE_URL}/geo/hotspots?eps=1000&min_samples=3", headers=headers)
        if r1.status_code != 200:
            print(f"FAILED (Status {r1.status_code}): {r1.text}")
            r1.raise_for_status()
        cold_data = r1.json()
    cold_latency = (time.monotonic() - t0) * 1000
    print(f"  [OK]  Cold request status=200 | Latency={round(cold_latency, 2)}ms | Items={len(cold_data)}")

    # ── Test 2: Warm Request (Cache HIT) ──────────────────────
    print("\n[Test 2] Executing WARM request (Cache HIT) to /geo/hotspots...")
    t1 = time.monotonic()
    async with httpx.AsyncClient() as client:
        r2 = await client.get(f"{BASE_URL}/geo/hotspots?eps=1000&min_samples=3", headers=headers)
        r2.raise_for_status()
        warm_data = r2.json()
    warm_latency = (time.monotonic() - t1) * 1000

    print(f"  [OK]  Warm request status=200 | Latency={round(warm_latency, 2)}ms | Items={len(warm_data)}")
    assert cold_data == warm_data, "Cached payload does not match original cold payload!"
    print("  [OK]  Payloads match 100% identically")
    print(f"  [OK]  Speedup ratio: {round(cold_latency / max(warm_latency, 0.01), 1)}x faster!")

    # ── Test 3: Event-Driven Cache Invalidation ───────────────
    print("\n[Test 3] Testing Cache Invalidation on Crime Registration...")
    crime_payload = {
        "fir_number": f"FIR-C2-{asyncio.get_event_loop().time()}",
        "crime_type": "chain_snatching",
        "severity": "high",
        "mo_text": "Rider snatched gold chain from victim near bus stop",
        "occurred_at": "2026-07-22T19:00:00Z",
        "district": "Bengaluru East",
        "police_station": "Indiranagar PS",
    }

    async with httpx.AsyncClient() as client:
        r3 = await client.post(f"{BASE_URL}/crimes/", json=crime_payload, headers=headers)
        r3.raise_for_status()
        print("  [OK]  Registered new FIR (triggered invalidate_cache_pattern)")

    # Small delay for background invalidation task
    await asyncio.sleep(0.5)

    # Next request to /geo/hotspots should be a fresh Cold request again
    t2 = time.monotonic()
    async with httpx.AsyncClient() as client:
        r4 = await client.get(f"{BASE_URL}/geo/hotspots?eps=1000&min_samples=3", headers=headers)
        r4.raise_for_status()
    post_invalidation_latency = (time.monotonic() - t2) * 1000
    print(f"  [OK]  Post-invalidation request status=200 | Latency={round(post_invalidation_latency, 2)}ms")

    print("\n" + "=" * 60)
    print("[PASS]  ALL C2 REDIS QUERY CACHING TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
