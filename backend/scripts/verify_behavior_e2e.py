"""
PAC Phase 3.3 — Behavior Intelligence E2E Verification & Benchmark Script
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

# Add parent path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy env vars for local script run if needed
os.environ["SECRET_KEY"] = "test-secret-key-for-verification-only"

from app.database import AsyncSessionLocal
from app.graph_db import get_graph_session, init_neo4j
from app.services.behavior_service import BehaviorService
from app.models.crime import Crime, CrimeType, CrimeSeverity
from app.models.criminal import Criminal, CrimeCriminal, CrimeRole
from app.models.crime_dna import CrimeDNA, DNAStatus
from app.services.dna_service import DNAService
from app.services.graph_service import GraphService
from sqlalchemy import select


async def main():
    print("=" * 60)
    print("PAC Behavior Intelligence E2E Verification & Benchmark — Phase 3.3")
    print("=" * 60)

    # 1. Initialize constraints
    print("\n[Step 1] Initializing Neo4j constraints...")
    await init_neo4j()
    print("  ✅ Constraints initialized.")

    async with AsyncSessionLocal() as db:
        async with get_graph_session() as graph_db:
            behavior_service = BehaviorService(db, graph_db)

            # 2. Rebuild all Profiles
            print("\n[Step 2] Triggering full behaviour profile rebuild...")
            t_start = time.time()
            counts = await behavior_service.rebuild_all_profiles()
            t_rebuild = (time.time() - t_start) * 1000
            print(f"  ✅ Rebuild complete in {t_rebuild:.2f}ms.")
            print(f"     Total profiles generated: {counts['total_rebuilt']}")

            # 3. Verify statistics
            print("\n[Step 3] Querying overall behavior statistics...")
            stats = await behavior_service.repo.get_statistics()
            print("  ✅ Statistics retrieved:")
            print(f"     Total Profiles: {stats['total_profiles']}")
            print(f"     Avg Risk Score: {stats['average_risk_score']}")
            print(f"     Avg Consistency Score: {stats['average_consistency_score']}")
            print(f"     Risk Level Distribution: {stats['risk_level_distribution']}")

            # 4. Create a synthetic criminal & crime pipeline to test auto-generation
            print("\n[Step 4] Testing Auto-Regeneration Pipeline...")
            
            # Register Criminal
            c1 = Criminal(
                id=uuid4(),
                name="E2E Behavior Subject",
                aliases=["Subject Alpha"],
                district="Bengaluru Urban",
                gang_name="E2E Gang",
                gang_affiliation=True,
                previous_cases_count=2
            )
            db.add(c1)
            await db.commit()
            print(f"  - Registered Criminal: {c1.name} (ID: {c1.id})")

            # Sync Criminal to Neo4j
            graph_svc = GraphService(db, graph_db)
            await graph_svc.sync_criminal(c1.id)

            # Register Crime
            crime = Crime(
                id=uuid4(),
                fir_number=f"FIR/BEHAVIOR/E2E/{int(time.time())}",
                crime_type=CrimeType.ROBBERY,
                severity=CrimeSeverity.CRITICAL,
                occurred_at=datetime.now(timezone.utc),
                district="Bengaluru Urban",
                police_station="Koramangala",
                latitude=12.9301,
                longitude=77.6201,
                mo_text="Suspect attacked delivery boy with a knife and snatched mobile phone."
            )
            db.add(crime)
            await db.commit()
            print(f"  - Registered Crime: {crime.fir_number} (ID: {crime.id})")

            # Associate Crime and Criminal
            link = CrimeCriminal(
                crime_id=crime.id,
                criminal_id=c1.id,
                role=CrimeRole.ACCUSED,
                is_arrested=True
            )
            db.add(link)
            await db.commit()
            print("  - Associated Criminal to Crime.")

            # Create CrimeDNA pending row
            dna_svc = DNAService(db)
            await dna_svc.create_pending(crime)
            
            # Populate DNA embedding manually to simulate ML Engine completion
            from app.repositories.dna_repo import DNARepository
            dna_repo = DNARepository(db)
            mock_emb = [0.05] * 384
            await dna_repo.mark_completed(
                crime.id,
                embedding=mock_emb,
                mo_text_embedded=crime.mo_text,
                crime_method="robbery",
                target_type="individual",
                weapon_used="knife",
                tools_used=["knife"],
                planning_level="opportunistic",
                gang_involved=True,
                escape_method="foot",
                modus_operandi_tags=["knife_attack", "snatching"]
            )
            await db.commit()
            print("  - DNA record marked as COMPLETED.")

            # Sync Crime to Neo4j (this triggers BehaviorService.generate_profile)
            print("  - Triggering Graph Sync (should auto-regenerate Behaviour Profile)...")
            from app.services.graph_service import sync_crime_to_graph
            await sync_crime_to_graph(crime.id)

            # Fetch the generated behavior profile
            profile = await behavior_service.repo.get_by_criminal_id(c1.id)
            if not profile:
                print("  ❌ Error: Behaviour profile was not generated!")
                return

            print("  ✅ Behavior Profile successfully generated:")
            print(f"     Risk Level: {profile.risk_level} (Score: {profile.risk_score})")
            print(f"     Consistency Score: {profile.behaviour_consistency_score}")
            print(f"     Violence Score: {profile.violence_score}")
            print(f"     Summary: {profile.profile_summary}")
            print(f"     Evidence facts recorded:")
            for ev in profile.detailed_metrics.get("evidence", []):
                print(f"       * {ev}")

            # 5. Performance Benchmarking
            print("\n[Step 5] Benchmarking Behaviour Profile generation performance...")
            bench_count = 10
            t_start_bench = time.time()
            for _ in range(bench_count):
                await behavior_service.generate_profile(c1.id)
            t_bench_total = (time.time() - t_start_bench) * 1000
            avg_latency = t_bench_total / bench_count
            print(f"  ✅ Benchmarked profile generation over {bench_count} runs.")
            print(f"     Total time: {t_bench_total:.2f}ms | Avg Latency: {avg_latency:.2f}ms per profile.")

            # 6. Cleanup E2E test data
            print("\n[Step 6] Cleaning up test data from PostgreSQL...")
            await db.delete(link)
            await db.delete(crime)
            await db.delete(c1)
            # Delete BehaviourProfile
            await db.delete(profile)
            # Delete CrimeDNA
            dna_res = await db.execute(select(CrimeDNA).where(CrimeDNA.crime_id == crime.id))
            dna_rec = dna_res.scalar_one_or_none()
            if dna_rec:
                await db.delete(dna_rec)
            await db.commit()
            print("  ✅ PostgreSQL cleanup complete.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 3.3 BEHAVIOR INTELLIGENCE E2E TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
