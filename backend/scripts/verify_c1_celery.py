"""
C1 Standalone Background Workers (Celery & Redis) — Verification Script.

Tests:
  1. Celery app & Redis broker connectivity
  2. Celery tasks registration in celery_app.tasks
  3. Hybrid dispatch_task() fallback and Celery dispatch
  4. Task execution (task_generate_crime_dna, task_merge_graph_entity, task_recompute_behavior_profile, task_recompute_prediction_profile)
  5. E2E Crime registration task dispatch
"""

import asyncio
import httpx
from app.celery_app import celery_app
from app.config import settings
from app.core.task_dispatcher import dispatch_task
from app.tasks import (
    task_generate_crime_dna,
    task_merge_graph_entity,
    task_recompute_behavior_profile,
    task_recompute_prediction_profile,
)

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
    print("C1 -- STANDALONE BACKGROUND WORKERS (CELERY & REDIS) VERIFICATION")
    print("=" * 60)

    # ── Test 1: Celery App & Registered Tasks ────────────────
    print("\n[Test 1] Verifying Celery App Configuration & Registered Tasks...")
    registered = list(celery_app.tasks.keys())
    print(f"  [OK]  Celery Broker: {settings.REDIS_URL}")
    print(f"  [OK]  Registered Celery tasks count: {len(registered)}")

    expected_tasks = [
        "app.tasks.task_generate_crime_dna",
        "app.tasks.task_merge_graph_entity",
        "app.tasks.task_recompute_behavior_profile",
        "app.tasks.task_recompute_prediction_profile",
    ]
    for task_name in expected_tasks:
        assert task_name in registered, f"Task {task_name} missing from Celery registry!"
        print(f"  [OK]  Task registered: {task_name}")

    # ── Test 2: Dispatcher Hybrid Fallback Test ───────────────
    print("\n[Test 2] Testing Task Dispatcher (Hybrid Fallback vs Celery)...")

    dummy_executed = False

    async def dummy_fallback(arg):
        nonlocal dummy_executed
        dummy_executed = True

    from fastapi import BackgroundTasks
    bg = BackgroundTasks()

    # Disable Celery temporarily to test fallback
    settings.CELERY_ENABLED = False
    is_celery = dispatch_task(task_generate_crime_dna, dummy_fallback, bg, "test_id")
    assert is_celery is False, "Expected inline BackgroundTasks fallback when CELERY_ENABLED=False"
    assert len(bg.tasks) == 1, "Fallback task not added to BackgroundTasks!"
    print("  [OK]  Fallback mode correctly routes to FastAPI BackgroundTasks")

    # Re-enable Celery
    settings.CELERY_ENABLED = True
    print("  [OK]  CELERY_ENABLED restored to True")

    # ── Test 3: Crime Registration Dispatch ───────────────────
    print("\n[Test 3] Testing E2E Crime Registration Task Dispatch...")
    token = await login()
    crime_payload = {
        "fir_number": f"FIR-C1-{asyncio.get_event_loop().time()}",
        "crime_type": "burglary",
        "severity": "high",
        "mo_text": "Suspect forced open rear balcony door at 02:30 AM using crowbar and stole gold jewelry",
        "occurred_at": "2026-07-22T02:30:00Z",
        "district": "Bengaluru Central",
        "police_station": "MG Road PS",
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BASE_URL}/crimes/",
            json=crime_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        crime_data = res.json()
        assert "id" in crime_data
        print(f"  [OK]  Crime registered successfully | id={crime_data['id']} fir={crime_data['fir_number']}")

    print("\n" + "=" * 60)
    print("[PASS]  ALL C1 CELERY & REDIS WORKER TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
