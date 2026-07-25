"""
CCTNS Data Ingestion & ETL Sync Pipeline — Verification Suite

Tests:
  1. Staging seeding & IPC section mapping rules
  2. ETL transformation: bilingual Kannada/English text cleansing and Crime entity creation
  3. Idempotency: re-running ETL produces 0 duplicate records
  4. HTTP API Endpoints (/cctns/seed-staging, /cctns/sync, /cctns/logs)
"""

import asyncio
import time
import httpx

from app.database import AsyncSessionLocal
from app.services.cctns_service import CCTNSEtlService, parse_ipc_section, sanitize_bilingual_narrative
from app.models.crime import CrimeType

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
    print("CCTNS DATA INGESTION & ETL SYNC VERIFICATION SUITE")
    print("=" * 60)

    # ── Test 1: Transformation Helper Unit Verification ────────
    print("\n[Test 1] Testing IPC Section Mapping Rules & Bilingual Cleansing...")
    assert parse_ipc_section("SEC_392_IPC") == CrimeType.ROBBERY, "Failed mapping SEC 392 IPC to ROBBERY"
    assert parse_ipc_section("SEC_379_IPC") == CrimeType.THEFT, "Failed mapping SEC 379 IPC to THEFT"
    assert parse_ipc_section("SEC_420_IPC") == CrimeType.CYBER_CRIME, "Failed mapping SEC 420 IPC to CYBER_CRIME"
    print("  [OK]  IPC section to CrimeType mapping rules verified (3/3)")

    kannada_raw = "  ರಾತ್ರಿ 8:30  ಸುಮಾರಿಗೆ \n\n bjjk.  "
    cleansed = sanitize_bilingual_narrative(kannada_raw)
    assert "  " not in cleansed and "\n" not in cleansed, "Failed whitespace cleansing"
    print(f"  [OK]  Bilingual text cleansing verified | result={cleansed!r}")

    # ── Test 2: Service-level ETL Execution ───────────────────
    print("\n[Test 2] Testing Service-level Staging & ETL Sync Pipeline...")
    async with AsyncSessionLocal() as session:
        service = CCTNSEtlService(session)
        seeded = await service.seed_staging_records(batch_size=3)
        print(f"  [OK]  Seeded {len(seeded)} staging FIR records")

        log1 = await service.run_etl_sync()
        print(f"  [OK]  ETL Run 1 | Extracted={log1.records_extracted} Imported={log1.records_imported} Status={log1.status.value}")
        assert log1.records_imported >= 3, "Failed to import seeded staging records!"

        # Test 3: Idempotency (re-run yields 0 new imports)
        log2 = await service.run_etl_sync()
        print(f"  [OK]  ETL Run 2 (Idempotency check) | Extracted={log2.records_extracted} Imported={log2.records_imported} Duplicates={log2.duplicates_skipped}")
        assert log2.records_imported == 0, "Idempotency failed: duplicate records were imported!"

    # ── Test 4: E2E HTTP API Endpoints ────────────────────────
    print("\n[Test 3] Testing E2E CCTNS HTTP API Endpoints...")
    token = await login()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        # Seed staging via API
        r_seed = await client.post(f"{BASE_URL}/cctns/seed-staging?batch_size=4", headers=headers)
        r_seed.raise_for_status()
        print(f"  [OK]  POST /cctns/seed-staging | Status=200 | Seeded={len(r_seed.json()['seeded_ids'])}")

        # Trigger sync via API
        r_sync = await client.post(f"{BASE_URL}/cctns/sync", headers=headers)
        r_sync.raise_for_status()
        sync_body = r_sync.json()
        print(f"  [OK]  POST /cctns/sync | Status=200 | {sync_body['message']}")

        # Fetch logs via API
        r_logs = await client.get(f"{BASE_URL}/cctns/logs", headers=headers)
        r_logs.raise_for_status()
        logs_data = r_logs.json()
        print(f"  [OK]  GET /cctns/logs | Status=200 | Historical log count={len(logs_data)}")
        assert len(logs_data) > 0, "No CCTNS import logs returned!"

    print("\n" + "=" * 60)
    print("[PASS]  ALL CCTNS ETL DATA INGESTION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
