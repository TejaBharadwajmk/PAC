"""
PAC — Seed DNA Generator (Phase 2.2)

Batch generates Crime DNA embeddings and intelligence fields for all existing crimes
in the database that do not have DNA records yet.

Usage (inside Docker):
  docker exec -it pac_backend python scripts/generate_seeded_dna.py
"""

import asyncio
import sys
import os
import time
from sqlalchemy import select

# Add parent path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.services.dna_service import DNAService
from app.repositories.dna_repo import DNARepository
from app.models.crime import Crime, CrimeMO
from app.models.crime_dna import CrimeDNA, DNAStatus

async def main():
    print("=" * 60)
    print("PAC Seed DNA Generator — Starting Batch Generation")
    print("=" * 60)
    
    t0 = time.time()
    
    async with AsyncSessionLocal() as session:
        # Get all crimes that do not have a CrimeDNA record at all
        result = await session.execute(
            select(Crime)
            .outerjoin(CrimeDNA, Crime.id == CrimeDNA.crime_id)
            .where(CrimeDNA.id.is_(None))
        )
        crimes = list(result.scalars().all())
        
        # Also query for any crimes where DNA status is PENDING or FAILED
        result_failed = await session.execute(
            select(CrimeDNA.crime_id)
            .where(CrimeDNA.status.in_([DNAStatus.PENDING, DNAStatus.FAILED]))
        )
        failed_or_pending_ids = [row[0] for row in result_failed.all()]
        
        total_to_create = len(crimes)
        total_to_generate = total_to_create + len(failed_or_pending_ids)
        
        print(f"Found {total_to_create} crimes with NO DNA record.")
        print(f"Found {len(failed_or_pending_ids)} existing records with PENDING/FAILED status.")
        print(f"Total DNA embeddings to generate: {total_to_generate}")
        
        if total_to_generate == 0:
            print("Everything is already generated. Exiting.")
            return

        # ── Step 1: Create PENDING records for new crimes ──────
        dna_svc = DNAService(session)
        if total_to_create > 0:
            print("Step 1: Creating PENDING DNA records in database...")
            count = 0
            for crime in crimes:
                mo_res = await session.execute(
                    select(CrimeMO).where(CrimeMO.crime_id == crime.id)
                )
                mo = mo_res.scalar_one_or_none()
                
                await dna_svc.create_pending(crime, mo)
                count += 1
                if count % 100 == 0 or count == total_to_create:
                    print(f"  Created PENDING record: {count}/{total_to_create}")
            
            await session.commit()
            print("PENDING records committed to DB successfully.")

    # ── Step 2: Generate embeddings ──────────────────────────
    # Re-fetch all IDs that need generation (either newly created or previously pending/failed)
    async with AsyncSessionLocal() as session:
        result_todo = await session.execute(
            select(CrimeDNA.crime_id)
            .where(CrimeDNA.status.in_([DNAStatus.PENDING, DNAStatus.FAILED]))
        )
        todo_ids = [row[0] for row in result_todo.all()]

    print("\nStep 2: Requesting embeddings from ML Engine /embed...")
    count = 0
    success_count = 0
    failed_count = 0
    
    # Instantiate DNAService for execution
    dna_svc = DNAService(None)
    
    for crime_id in todo_ids:
        try:
            # generate() opens its own DB session so it's safe to call in isolation
            await dna_svc.generate(crime_id)
            
            # Verify if it succeeded
            async with AsyncSessionLocal() as check_session:
                res = await check_session.execute(
                    select(CrimeDNA.status).where(CrimeDNA.crime_id == crime_id)
                )
                status = res.scalar_one_or_none()
                if status == DNAStatus.COMPLETED:
                    success_count += 1
                else:
                    failed_count += 1
        except Exception as e:
            failed_count += 1
            print(f"  [ERROR] Crime {crime_id} failed: {e}")
            
        count += 1
        if count % 50 == 0 or count == len(todo_ids):
            elapsed = time.time() - t0
            rate = count / elapsed if elapsed > 0 else 0
            print(f"  Processed: {count}/{len(todo_ids)} | Success: {success_count} | Failed: {failed_count} | Rate: {rate:.1f} records/sec")

    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print("Batch Generation Complete!")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {failed_count}")
    print(f"  Time:    {elapsed:.1f} seconds")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(1)
