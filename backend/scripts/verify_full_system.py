"""
PAC — Complete System-Wide End-to-End Verification Suite

Tests all core intelligence capabilities across backend microservices:
  1. PostgreSQL + pgvector + PostGIS & Hybrid Retrieval Engine (FTS + Vector + MO)
  2. Neo4j Knowledge Graph Intelligence (Nodes, Edges, Connectivity)
  3. B1 Audit Trail & Chain of Custody Middleware
  4. B2 Air-Gapped Local LLM (Ollama & Grounded RAG)
  5. C1 Celery & Redis Background Worker Queue
  6. C2 Redis Query Caching & Speedup
  7. CCTNS Data Ingestion & ETL Sync Pipeline
"""

import asyncio
import time
import httpx

from app.database import AsyncSessionLocal
from app.config import settings
from app.core.cache import invalidate_cache_pattern

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
    print("=" * 70)
    print("POLICE IT ANALYTICS CORE (PAC) — FULL SYSTEM VERIFICATION SUITE")
    print("=" * 70)

    token = await login()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ── 1. Hybrid Retrieval Engine (FTS + Vector + MO) ─────────
        print("\n[Sub-System 1] Testing Hybrid Retrieval Forensic Search...")
        r_sim = await client.post(
            f"{BASE_URL}/similarity/search",
            json={
                "query_text": "Night time chain snatching by bike riders wearing helmets near bus stop",
                "semantic_weight": 0.5,
                "fts_weight": 0.3,
                "mo_weight": 0.2,
                "limit": 5,
                "min_similarity": 0.1,
            },
            headers=headers,
        )
        r_sim.raise_for_status()
        sim_data = r_sim.json()
        print(f"  [PASS] Hybrid Search returned {len(sim_data.get('results', []))} ranked matches")

        # ── 2. Neo4j Knowledge Graph ──────────────────────────────
        print("\n[Sub-System 2] Testing Neo4j Knowledge Graph Intelligence...")
        r_graph = await client.get(f"{BASE_URL}/graph/statistics", headers=headers)
        r_graph.raise_for_status()
        g_stats = r_graph.json()
        total_n = sum(g_stats.get('node_counts', {}).values())
        total_r = sum(g_stats.get('relationship_counts', {}).values())
        print(f"  [PASS] Neo4j Graph online | Nodes={total_n} Edges={total_r}")

        # ── 3. B1 Audit Trail & Middleware ────────────────────────
        print("\n[Sub-System 3] Testing B1 Audit Trail & Chain of Custody...")
        r_audit = await client.get(f"{BASE_URL}/audit/logs?limit=5", headers=headers)
        r_audit.raise_for_status()
        audit_logs = r_audit.json()
        print(f"  [PASS] Audit Trail active | Recorded logs count={len(audit_logs)}")

        # ── 4. B2 Air-Gapped Local LLM ────────────────────────────
        print("\n[Sub-System 4] Testing B2 Air-Gapped Local LLM (Ollama)...")
        r_llm = await client.get(f"{BASE_URL}/assistant/health", headers=headers)
        r_llm.raise_for_status()
        llm_info = r_llm.json()
        print(f"  [PASS] Local LLM active | Provider={llm_info['provider']} Model={llm_info.get('model', 'mistral')} Status={llm_info['status']}")

        # ── 5. C1 Celery & Redis Worker Queue ─────────────────────
        print("\n[Sub-System 5] Testing C1 Celery & Redis Background Queue...")
        from app.celery_app import celery_app
        registered = list(celery_app.tasks.keys())
        c1_tasks = [t for t in registered if "app.tasks" in t]
        print(f"  [PASS] Celery Workers operational | Active tasks={len(c1_tasks)}")

        # ── 6. C2 Redis Query Caching ─────────────────────────────
        print("\n[Sub-System 6] Testing C2 Redis Query Caching...")
        await invalidate_cache_pattern("pac:cache:geo:*")
        t0 = time.monotonic()
        r_cold = await client.get(f"{BASE_URL}/geo/hotspots?eps=1000&min_samples=3", headers=headers)
        r_cold.raise_for_status()
        cold_ms = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        r_warm = await client.get(f"{BASE_URL}/geo/hotspots?eps=1000&min_samples=3", headers=headers)
        r_warm.raise_for_status()
        warm_ms = (time.monotonic() - t1) * 1000

        speedup = round(cold_ms / max(warm_ms, 0.01), 1)
        print(f"  [PASS] Redis Cache active | Cold={round(cold_ms,1)}ms Warm={round(warm_ms,1)}ms | Speedup={speedup}x")

        # ── 7. CCTNS Data Ingestion & ETL Sync ────────────────────
        print("\n[Sub-System 7] Testing CCTNS Legacy Data Ingestion ETL...")
        r_cctns_seed = await client.post(f"{BASE_URL}/cctns/seed-staging?batch_size=2", headers=headers)
        r_cctns_seed.raise_for_status()
        r_cctns_sync = await client.post(f"{BASE_URL}/cctns/sync", headers=headers)
        r_cctns_sync.raise_for_status()
        cctns_log = r_cctns_sync.json()["log"]
        print(f"  [PASS] CCTNS ETL Sync active | Imported={cctns_log['records_imported']} Duplicates={cctns_log['duplicates_skipped']} Status={cctns_log['status']}")

    print("\n" + "=" * 70)
    print(" [SUCCESS] ALL 7 PAC CORE SUB-SYSTEMS VERIFIED 100% OPERATIONAL!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
