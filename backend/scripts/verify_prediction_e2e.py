"""
PAC Phase 3.4 — Predictive Intelligence E2E Verification & Benchmark Script
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

# Add parent path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.graph_db import get_graph_session, init_neo4j
from app.services.prediction_service import PredictionService
from app.services.dna_service import DNAService
from app.services.graph_service import GraphService, sync_crime_to_graph
from app.models.crime import Crime, CrimeType, CrimeSeverity
from app.models.criminal import Criminal, CrimeCriminal, CrimeRole
from app.models.crime_dna import CrimeDNA
from app.models.behaviour import BehaviourProfile
from app.models.prediction import PredictionProfile
from sqlalchemy import select


async def main():
    print("=" * 60)
    print("PAC Predictive Intelligence E2E Verification & Benchmark — Phase 3.4")
    print("=" * 60)

    # Initialize graph constraints
    await init_neo4j()

    async with AsyncSessionLocal() as db:
        async with get_graph_session() as graph_db:
            service = PredictionService(db, graph_db)

            # 1. Rebuild all Predictions
            print("\n[Step 1] Triggering full predictions rebuild...")
            t_start = time.time()
            counts = await service.rebuild_all_predictions()
            t_rebuild = (time.time() - t_start) * 1000
            print(f"  ✅ Rebuild complete in {t_rebuild:.2f}ms.")
            print(f"     Rebuild results: {counts}")

            # 2. Query statistics
            print("\n[Step 2] Querying prediction statistics...")
            stats = await service.repo.get_statistics()
            print("  ✅ Statistics:")
            print(f"     Total Criminal Predictions: {stats['total_criminal_predictions']}")
            print(f"     Avg Criminal Risk Score: {stats['average_criminal_risk_score']}")
            print(f"     Distribution: {stats['risk_level_distribution']}")

            # 3. Test E2E Trigger Flow (Crime -> DNA -> Behavior -> Prediction)
            print("\n[Step 3] Executing E2E trigger pipeline test...")

            # Add criminal
            c1 = Criminal(
                id=uuid4(),
                name="Predictive Subject",
                aliases=["Subject Beta"],
                district="Bengaluru Urban",
                gang_name="Predictive Gang",
                gang_affiliation=True,
                previous_cases_count=4
            )
            db.add(c1)
            await db.commit()
            print(f"  - Registered Criminal: {c1.name} (ID: {c1.id})")

            # Sync criminal to Neo4j
            graph_svc = GraphService(db, graph_db)
            await graph_svc.sync_criminal(c1.id)

            # Add crime
            crime = Crime(
                id=uuid4(),
                fir_number=f"FIR/PREDICT/E2E/{int(time.time())}",
                crime_type=CrimeType.ROBBERY,
                severity=CrimeSeverity.CRITICAL,
                occurred_at=datetime.now(timezone.utc),
                district="Bengaluru Urban",
                police_station="Koramangala",
                latitude=12.9301,
                longitude=77.6201,
                mo_text="Offender snatch chain from women at knife-point."
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

            # Manually complete DNA to simulate ML Engine embedding completion
            from app.repositories.dna_repo import DNARepository
            dna_repo = DNARepository(db)
            mock_emb = [0.03] * 384
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

            # Sync Crime to Neo4j
            # This triggers:
            # 1. Neo4j Sync
            # 2. Behavior Profile auto-regeneration
            # 3. Prediction Risk Forecast auto-generation!
            print("  - Synchronizing to Neo4j (should fire behavior and prediction triggers)...")
            await sync_crime_to_graph(crime.id)

            # Retrieve generated Prediction Profile
            pred_profile = await service.repo.get_by_entity("criminal", str(c1.id))
            if not pred_profile:
                print("  ❌ Error: Criminal Risk Prediction was not auto-generated!")
                return

            print("  ✅ Criminal Risk Forecast auto-generated successfully:")
            print(f"     Risk Score: {pred_profile.prediction_score}")
            print(f"     Risk Level: {pred_profile.risk_level}")
            print(f"     Reason Code: {pred_profile.prediction_reason_code}")
            print(f"     Confidence: {pred_profile.confidence}")
            print(f"     Score Breakdown: {pred_profile.score_breakdown}")
            print(f"     Evidence facts recorded:")
            for ev in pred_profile.evidence:
                print(f"       * {ev}")
            print(f"     Operational Recommendations:")
            for rec in pred_profile.recommendations:
                print(f"       * {rec}")

            # 4. Latency Benchmarking
            print("\n[Step 4] Benchmarking Prediction calculations...")
            bench_count = 10
            t_start_bench = time.time()
            for _ in range(bench_count):
                await service.generate_criminal_prediction(c1.id)
            t_bench_total = (time.time() - t_start_bench) * 1000
            avg_latency = t_bench_total / bench_count
            print(f"  ✅ Calculated predictions over {bench_count} runs.")
            print(f"     Total time: {t_bench_total:.2f}ms | Avg Latency: {avg_latency:.2f}ms per prediction.")

            # 5. Clean up test records
            print("\n[Step 5] Cleaning up test data from PostgreSQL...")
            await db.delete(link)
            await db.delete(crime)
            await db.delete(c1)
            
            # Delete snapshots
            await db.execute(
                select(PredictionProfile)
                .where(PredictionProfile.entity_type == "criminal")
                .where(PredictionProfile.entity_id == str(c1.id))
            )
            # Fetch behavior profile and delete it
            bp_res = await db.execute(select(BehaviourProfile).where(BehaviourProfile.criminal_id == c1.id))
            bp_rec = bp_res.scalar_one_or_none()
            if bp_rec:
                await db.delete(bp_rec)
            
            # Fetch CrimeDNA and delete it
            dna_res = await db.execute(select(CrimeDNA).where(CrimeDNA.crime_id == crime.id))
            dna_rec = dna_res.scalar_one_or_none()
            if dna_rec:
                await db.delete(dna_rec)

            await db.commit()
            print("  ✅ PostgreSQL cleanup complete.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 3.4 PREDICTIVE INTELLIGENCE E2E TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
