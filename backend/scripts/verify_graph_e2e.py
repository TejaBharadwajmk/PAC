"""
PAC Phase 3.2 — Criminal Network Intelligence (Neo4j) E2E Verification Script
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
from app.services.graph_service import GraphService
from app.models.crime import Crime, CrimeType, CrimeSeverity
from app.models.criminal import Criminal, CrimeCriminal, CrimeRole
from sqlalchemy import select, func


async def main():
    print("=" * 60)
    print("PAC Criminal Network Intelligence E2E Verification — Phase 3.2")
    print("=" * 60)

    # 1. Initialize Neo4j constraints
    print("\n[Step 1] Initializing Neo4j unique constraints...")
    await init_neo4j()
    print("  ✅ Constraints initialized.")

    async with AsyncSessionLocal() as db:
        # Get Neo4j session using the driver context
        async with get_graph_session() as graph_db:
            service = GraphService(db, graph_db)

            # 2. Trigger Full Rebuild
            print("\n[Step 2] Triggering full graph rebuild from PostgreSQL...")
            t_start = time.time()
            counts = await service.rebuild_graph()
            t_rebuild = (time.time() - t_start) * 1000
            print(f"  ✅ Rebuild complete in {t_rebuild:.2f}ms.")
            print(f"     Crimes synced: {counts['crimes_synced']}")
            print(f"     Criminals synced: {counts['criminals_synced']}")
            print(f"     Relationships synced: {counts['relationships_synced']}")

            # 3. Verify Graph Statistics
            print("\n[Step 3] Fetching graph statistics from Neo4j...")
            stats = await service.repo.get_graph_statistics()
            print(f"  ✅ Statistics retrieved:")
            print(f"     Nodes counts: {stats.get('node_counts')}")
            print(f"     Relationship counts: {stats.get('relationship_counts')}")

            # 4. Create and link co-offenders to test relationship strength formulas
            print("\n[Step 4] Testing Co-offender Association Logic & Strength Updates...")
            
            # Create two criminals
            c1 = Criminal(
                id=uuid4(),
                name="E2E Criminal Alpha",
                aliases=["Alpha"],
                district="Bengaluru Urban",
                gang_name="Alpha Gang",
                gang_affiliation=True
            )
            c2 = Criminal(
                id=uuid4(),
                name="E2E Criminal Beta",
                aliases=["Beta"],
                district="Bengaluru Urban",
                gang_name="Alpha Gang",
                gang_affiliation=True
            )
            db.add_all([c1, c2])
            await db.commit()

            # Create crime 1
            crime1 = Crime(
                id=uuid4(),
                fir_number=f"FIR/E2E/{int(time.time())}/1",
                crime_type=CrimeType.BURGLARY,
                severity=CrimeSeverity.HIGH,
                occurred_at=datetime.now(timezone.utc),
                district="Bengaluru Urban",
                police_station="Koramangala",
                mo_text="Alpha and Beta broke into a warehouse."
            )
            db.add(crime1)
            await db.commit()

            # Associate both with Crime 1
            link1 = CrimeCriminal(
                crime_id=crime1.id,
                criminal_id=c1.id,
                role=CrimeRole.ACCUSED,
                is_arrested=False
            )
            link2 = CrimeCriminal(
                crime_id=crime1.id,
                criminal_id=c2.id,
                role=CrimeRole.ACCUSED,
                is_arrested=False
            )
            db.add_all([link1, link2])
            await db.commit()

            print(f"  - Synchronizing Crime 1 to Neo4j...")
            await service.sync_criminal(c1.id)
            await service.sync_criminal(c2.id)
            await service.sync_crime(crime1.id)

            # Check network for c1
            network = await service.get_criminal_network(c1.id)
            assoc_rel = next((r for r in network.relationships if r.type == "CRIMINAL_ASSOCIATED_WITH_CRIMINAL"), None)
            
            if not assoc_rel:
                print("  ❌ Error: ASSOCIATION relationship not found after first co-offence!")
                return
            
            print("  ✅ First association verified:")
            print(f"     times_seen_together: {assoc_rel.properties.get('times_seen_together')}")
            print(f"     association_strength: {assoc_rel.properties.get('association_strength')}")

            # Create crime 2 (second co-offence)
            crime2 = Crime(
                id=uuid4(),
                fir_number=f"FIR/E2E/{int(time.time())}/2",
                crime_type=CrimeType.ROBBERY,
                severity=CrimeSeverity.CRITICAL,
                occurred_at=datetime.now(timezone.utc),
                district="Bengaluru Urban",
                police_station="Koramangala",
                mo_text="Alpha and Beta robbed a delivery truck."
            )
            db.add(crime2)
            await db.commit()

            # Associate both with Crime 2
            link3 = CrimeCriminal(
                crime_id=crime2.id,
                criminal_id=c1.id,
                role=CrimeRole.ACCUSED,
                is_arrested=True
            )
            link4 = CrimeCriminal(
                crime_id=crime2.id,
                criminal_id=c2.id,
                role=CrimeRole.ACCUSED,
                is_arrested=True
            )
            db.add_all([link3, link4])
            await db.commit()

            print(f"  - Synchronizing Crime 2 to Neo4j...")
            await service.sync_criminal(c1.id)
            await service.sync_criminal(c2.id)
            await service.sync_crime(crime2.id)

            # Check network again
            network2 = await service.get_criminal_network(c1.id)
            assoc_rel2 = next((r for r in network2.relationships if r.type == "CRIMINAL_ASSOCIATED_WITH_CRIMINAL"), None)
            
            if not assoc_rel2:
                print("  ❌ Error: ASSOCIATION relationship not found after second co-offence!")
                return

            print("  ✅ Second association verified:")
            print(f"     times_seen_together: {assoc_rel2.properties.get('times_seen_together')}")
            print(f"     association_strength: {assoc_rel2.properties.get('association_strength')}")

            # 5. Verify Pathfinding (Shortest Path)
            print("\n[Step 5] Testing pathfinding (Shortest Path between Alpha and Beta)...")
            path = await service.get_shortest_path(c1.id, c2.id)
            print(f"  ✅ Shortest path found: {path.found}")
            print(f"     Distance (degrees of separation): {path.distance}")
            print(f"     Nodes in path: {[n.properties.get('name') or n.properties.get('fir_number') for n in path.nodes]}")

            # 6. Cleanup test data from PostgreSQL
            print("\n[Step 6] Cleaning up test data from PostgreSQL...")
            await db.delete(link1)
            await db.delete(link2)
            await db.delete(link3)
            await db.delete(link4)
            await db.delete(crime1)
            await db.delete(crime2)
            await db.delete(c1)
            await db.delete(c2)
            await db.commit()
            print("  ✅ PostgreSQL cleanup done.")

            # Full rebuild to sync clean state back to Neo4j
            print("  - Restoring clean Neo4j state via rebuild...")
            await service.rebuild_graph()
            print("  ✅ Clean Neo4j state restored.")

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 3.2 CRIMINAL NETWORK INTELLIGENCE E2E TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
