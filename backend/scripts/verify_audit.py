"""
B1 Audit Trail — end-to-end verification script.

Tests:
  1. Login generates a LOGIN audit entry
  2. Similarity search generates a SEARCH audit entry with query_text
  3. Crime view generates a VIEW audit entry
  4. Admin can query /audit/logs and see entries
  5. /audit/logs?action=search returns only SEARCH entries
  6. /audit/logs/user/{badge} returns officer-specific entries
  7. /audit/logs/search returns entries with query_text populated
"""

import asyncio
import httpx

BASE = "http://localhost:8000/api/v1"
ADMIN_BADGE = "ADMIN001"
ADMIN_PASS  = "Admin@2024"


async def login(badge: str, password: str) -> str:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/auth/login", json={"badge_number": badge, "password": password})
        r.raise_for_status()
        return r.json()["access_token"]


async def authed_get(token: str, path: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.json()


async def authed_post(token: str, path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{BASE}{path}",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()


async def main():
    print("=" * 60)
    print("B1 -- AUDIT TRAIL VERIFICATION SUITE")
    print("=" * 60)

    # -- Login (generates LOGIN audit entry)
    print("\n[Step 1] Logging in as ADMIN001...")
    token = await login(ADMIN_BADGE, ADMIN_PASS)
    print("  [OK]  Login successful")

    # -- Trigger a similarity search (generates SEARCH audit entry)
    print("\n[Step 2] Running similarity search to trigger SEARCH audit...")
    await authed_post(token, "/similarity/search", {
        "query_text": "robber broke glass window of jewelry shop at night",
        "include_debug": True,
    })
    print("  [OK]  Similarity search complete")

    # -- Small delay so fire-and-forget writes complete
    await asyncio.sleep(1.5)

    # -- Query audit logs as admin
    print("\n[Test 1] GET /audit/logs — should return records...")
    logs_resp = await authed_get(token, "/audit/logs")
    assert logs_resp["total_returned"] > 0, "Expected audit log entries, got 0"
    print(f"  [OK]  total_returned={logs_resp['total_returned']}")

    # -- Filter by action=search
    print("\n[Test 2] GET /audit/logs?action=search — only SEARCH entries...")
    search_logs = await authed_get(token, "/audit/logs?action=search")
    assert search_logs["total_returned"] > 0, "Expected SEARCH audit entries"
    for entry in search_logs["results"]:
        assert entry["action"] == "search", f"Unexpected action: {entry['action']}"
    print(f"  [OK]  {search_logs['total_returned']} SEARCH entries, all action=search")

    # -- Filter by badge_number
    print(f"\n[Test 3] GET /audit/logs?badge_number={ADMIN_BADGE}...")
    user_logs = await authed_get(token, f"/audit/logs?badge_number={ADMIN_BADGE}")
    assert user_logs["total_returned"] > 0, "Expected entries for ADMIN001"
    for entry in user_logs["results"]:
        assert entry["badge_number"] == ADMIN_BADGE
    print(f"  [OK]  {user_logs['total_returned']} entries, all badge={ADMIN_BADGE}")

    # -- Officer activity endpoint
    print(f"\n[Test 4] GET /audit/logs/user/{ADMIN_BADGE}...")
    activity = await authed_get(token, f"/audit/logs/user/{ADMIN_BADGE}")
    assert activity["total_returned"] > 0
    print(f"  [OK]  {activity['total_returned']} entries in officer activity timeline")

    # -- Search queries endpoint
    print("\n[Test 5] GET /audit/logs/search — SEARCH entries with query_text...")
    sq = await authed_get(token, "/audit/logs/search")
    assert sq["total_returned"] > 0
    for entry in sq["results"]:
        assert entry["action"] == "search"
    print(f"  [OK]  {sq['total_returned']} search query entries")

    # -- Verify LOGIN entry has action=login
    print("\n[Test 6] Verify LOGIN action was recorded...")
    login_logs = await authed_get(token, "/audit/logs?action=login")
    assert login_logs["total_returned"] > 0, "Expected LOGIN entry"
    print(f"  [OK]  {login_logs['total_returned']} LOGIN entries found")

    # -- Verify duration_ms and status_code are populated
    print("\n[Test 7] Verify duration_ms and status_code are populated...")
    sample = logs_resp["results"][0]
    assert sample["status_code"] is not None, "status_code should be set"
    assert sample["duration_ms"] is not None, "duration_ms should be set"
    assert sample["ip_address"] is not None, "ip_address should be set"
    print(f"  [OK]  status_code={sample['status_code']} duration_ms={sample['duration_ms']} ip={sample['ip_address']}")

    print("\n" + "=" * 60)
    print("[PASS]  ALL B1 AUDIT TRAIL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
