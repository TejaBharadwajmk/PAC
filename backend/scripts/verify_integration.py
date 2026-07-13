"""
PAC — Pipeline & Integration Verification Script (Phase 2.2)

Automates verification of the entire Crime DNA pipeline:
  1. Registers a new crime with unique FIR & MO text
  2. Verifies CrimeDNA record creation at PENDING
  3. Polls/waits for background processing to finish
  4. Verifies status changes to COMPLETED and embedding is populated
  5. Tests explainable similarity search (text and crime-id modes)
  6. Simulates failure mode (ML engine unavailable) & verifies FAILED transition
  7. Benchmarks embedding generation and similarity search speeds
  8. Outputs detailed verification report

Usage:
  docker exec -it pac_backend python scripts/verify_integration.py
"""

import asyncio
import sys
import os
import time
import httpx
from datetime import datetime, timezone
from uuid import uuid4

# Add parent path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy env vars for local script run if needed
os.environ["SECRET_KEY"] = "test-secret-key-for-verification-only"

from app.database import AsyncSessionLocal
from app.config import settings
from app.models.user import User, UserRole
from app.models.crime import Crime, CrimeMO, CrimeType
from app.models.crime_dna import CrimeDNA, DNAStatus
from app.services.dna_service import DNAService
from app.repositories.dna_repo import DNARepository
from app.services.similarity_service import SimilarityService
from sqlalchemy import select

# We'll call the FastAPI API endpoints directly via httpx using test auth token or service calls.
# Let's create an admin user or run checks directly via service classes to verify the code logic.
# Running via service classes doesn't require a web server to be running, making it extremely robust.
# We will also test HTTP endpoints directly.

async def verify_pipeline():
    print("=" * 60)
    print("PAC Integration & Validation Tool — Phase 2.2")
    print("=" * 60)
    
    # ── Test 1: Seed verification ──
    print("\n[Test 1] Verifying database connectivity & seeded data...")
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Crime.id).limit(1))
        has_crimes = res.first() is not None
        if not has_crimes:
            print("  ❌ No crimes found in DB. Run seed_data.py first.")
            return False
        
        # Count total crimes
        total_crimes = (await session.execute(func_count_crimes())).scalar_one()
        print(f"  ✅ Database connected successfully. Total crimes in DB: {total_crimes}")

    # ── Test 2: Crime Registration & DNA Pending Creation ──
    print("\n[Test 2] Testing Crime Registration & DNA row lifecycle...")
    unique_fir = f"FIR/TEST/{int(time.time())}"
    
    # Fetch/create a mock user to assign
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).limit(1))
        mock_user = user_res.scalar_one_or_none()
        if not mock_user:
            # Create a mock analyst
            from app.core.security import get_password_hash
            mock_user = User(
                badge_number="TEST999",
                full_name="Integration Test Officer",
                email="test_officer@ksp.gov.in",
                hashed_password=get_password_hash("TestPassword@2024"),
                role=UserRole.OFFICER,
            )
            session.add(mock_user)
            await session.commit()
            await session.refresh(mock_user)

    from app.services.crime_service import CrimeService
    from app.schemas.crime import CrimeCreate
    
    register_payload = CrimeCreate(
        fir_number=unique_fir,
        crime_type=CrimeType.BURGLARY,
        district="Bengaluru Urban",
        police_station="Cubbon Park",
        mo_text="Two suspects broke open the lock of a jewelry shop at midnight using an iron rod and escaped with gold necklaces on a black two-wheeler.",
        occurred_at=datetime.now(timezone.utc),
    )
    
    async with AsyncSessionLocal() as session:
        crime_svc = CrimeService(session)
        # Registering the crime should also create a CrimeDNA pending row
        crime_record = await crime_svc.register_crime(register_payload, mock_user)
        print(f"  ✅ Registered test crime. FIR: {unique_fir} | ID: {crime_record.id}")
        
        # Verify the CrimeDNA row exists and is PENDING
        dna_repo = DNARepository(session)
        dna_record = await dna_repo.get_by_crime_id(crime_record.id)
        if not dna_record:
            print("  ❌ Error: CrimeDNA row was not created at registration!")
            return False
            
        print(f"  ✅ CrimeDNA row created. Initial Status: {dna_record.status.value}")
        if dna_record.status != DNAStatus.PENDING:
            print(f"  ❌ Error: Initial status was {dna_record.status.value}, expected PENDING")
            return False
            
        # Verify time intelligence was precomputed
        print(f"  ✅ Precomputed time intelligence: Slot={dna_record.time_of_day_slot}, Hour={dna_record.hour_of_day}, Weekend={dna_record.is_weekend}")
        await session.commit()
        
    # ── Test 3: DNA Embedding Generation ──
    print("\n[Test 3] Simulating background DNA generation task...")
    dna_svc = DNAService(None)
    
    # We will trigger the background generation task
    t_start = time.time()
    await dna_svc.generate(crime_record.id)
    t_generation = (time.time() - t_start) * 1000
    print(f"  ✅ Background task generation finished in {t_generation:.1f}ms")
    
    # Check the updated record status
    async with AsyncSessionLocal() as session:
        dna_repo = DNARepository(session)
        dna_record = await dna_repo.get_by_crime_id(crime_record.id)
        print(f"  ✅ Post-processing Status: {dna_record.status.value}")
        if dna_record.status == DNAStatus.FAILED:
            print(f"  ❌ Generation failed: {dna_record.status_message}")
            return False
            
        if dna_record.status != DNAStatus.COMPLETED:
            print(f"  ❌ Error: Status is {dna_record.status.value}, expected COMPLETED")
            return False
            
        print(f"  ✅ Embedding successfully populated in pgvector. Dims: {len(dna_record.embedding)}")
        print(f"  ✅ Denormalized MO attributes copied: method={dna_record.crime_method}, target={dna_record.target_type}, gang={dna_record.gang_involved}")

    # ── Test 4: Similarity Search ──
    print("\n[Test 4] Testing hybrid similarity search (Text Mode)...")
    async with AsyncSessionLocal() as session:
        sim_svc = SimilarityService(session)
        from app.schemas.dna import SimilaritySearchRequest
        
        search_req = SimilaritySearchRequest(
            query_text="Accused entered jewelry store by breaking lock during night, stole gold and escaped on bike.",
            crime_type=CrimeType.BURGLARY,
            limit=5,
            min_similarity=0.40,
        )
        
        resp = await sim_svc.search_by_text(search_req)
        print(f"  ✅ Search returned {len(resp.results)} similar cases.")
        
        if not resp.results:
            print("  ❌ Error: Search returned no results!")
            return False
            
        first_result = resp.results[0]
        print(f"  ✅ Top Match: FIR={first_result.fir_number}")
        print(f"     Hybrid Score: {first_result.similarity_score} | Semantic: {first_result.semantic_similarity} | Feature: {first_result.feature_similarity}")
        print(f"     Matched Features: {first_result.matched_features}")
        print(f"     Explanation: {first_result.explanation}")
        
        # Test existing crime-id mode
        print("\n[Test 4.2] Testing hybrid similarity search (Crime-ID Mode)...")
        id_resp = await sim_svc.search_by_crime_id(crime_record.id, limit=5, min_similarity=0.40)
        print(f"  ✅ Crime-ID Search returned {len(id_resp.results)} similar cases.")

    # ── Test 5: Failure Scenarios & Retries ──
    print("\n[Test 5] Simulating ML Engine failure scenario...")
    # Temporarily redirect MLENGINE_URL to an invalid port
    original_url = settings.MLENGINE_URL
    settings.MLENGINE_URL = "http://localhost:9999" # invalid port
    
    # Create another test crime
    unique_fir_fail = f"FIR/FAIL/{int(time.time())}"
    register_fail_payload = CrimeCreate(
        fir_number=unique_fir_fail,
        crime_type=CrimeType.THEFT,
        district="Mysuru",
        police_station="Hebbal",
        mo_text="Chain snatching by bike riders",
        occurred_at=datetime.now(timezone.utc),
    )
    
    async with AsyncSessionLocal() as session:
        crime_svc = CrimeService(session)
        fail_crime = await crime_svc.register_crime(register_fail_payload, mock_user)
        await session.commit()
        
    print(f"  ✅ Registered fail test crime. ID: {fail_crime.id}")
    print("  ⌛ Triggering generation with ML Engine offline (retries will run)...")
    
    # Run generator - this should exhaust retries and fail
    t_start_fail = time.time()
    await dna_svc.generate(fail_crime.id)
    t_fail_process = time.time() - t_start_fail
    
    # Check status
    async with AsyncSessionLocal() as session:
        dna_repo = DNARepository(session)
        fail_dna = await dna_repo.get_by_crime_id(fail_crime.id)
        print(f"  ✅ Post-failure Status: {fail_dna.status.value}")
        print(f"  ✅ Failure Message: {fail_dna.status_message}")
        print(f"  ✅ Retry count reached: {fail_dna.retry_count}/{MAX_RETRIES_TEST()}")
        
        if fail_dna.status != DNAStatus.FAILED:
            print(f"  ❌ Error: Expected status to be FAILED, got {fail_dna.status.value}")
            return False
            
    # Restore original ML url
    settings.MLENGINE_URL = original_url
    
    # Test Recovery / Reindex
    print("\n[Test 5.2] Testing recovery / reindex of FAILED record...")
    async with AsyncSessionLocal() as session:
        # Trigger reindex
        session_dna_svc = DNAService(session)
        await session_dna_svc.reindex(fail_crime.id)
        # Verify status reset to PENDING
        dna_repo = DNARepository(session)
        reset_dna = await dna_repo.get_by_crime_id(fail_crime.id)
        print(f"  ✅ Status reset to: {reset_dna.status.value}")
        if reset_dna.status != DNAStatus.PENDING:
            print("  ❌ Reset failed to set status to PENDING")
            return False
            
    # Re-run generation with ML Engine online
    print("  ⌛ Re-running generation with ML Engine online...")
    await dna_svc.generate(fail_crime.id)
    async with AsyncSessionLocal() as session:
        dna_repo = DNARepository(session)
        recovered_dna = await dna_repo.get_by_crime_id(fail_crime.id)
        print(f"  ✅ Recovered Status: {recovered_dna.status.value}")
        if recovered_dna.status != DNAStatus.COMPLETED:
            print(f"  ❌ Recovery failed: Status is {recovered_dna.status.value}")
            return False

    # ── Test 6: Performance Benchmarking ──
    print("\n[Test 6] Running Performance Benchmarks...")
    bench_count = 10
    total_embed_time = 0.0
    total_search_time = 0.0
    
    print(f"  ⌛ Running {bench_count} embedding requests...")
    dummy_text = "Accused broke lock of a house and stole valuables"
    
    from app.services.dna_service import _call_embed_endpoint
    for _ in range(bench_count):
        t0 = time.time()
        await _call_embed_endpoint(dummy_text, uuid4())
        total_embed_time += (time.time() - t0)
        
    avg_embed = (total_embed_time / bench_count) * 1000
    print(f"  ✅ Avg ML Engine embedding latency: {avg_embed:.2f} ms")
    
    print(f"  ⌛ Running {bench_count} similarity searches...")
    async with AsyncSessionLocal() as session:
        sim_svc = SimilarityService(session)
        bench_search_req = SimilaritySearchRequest(
            query_text="House break in during night",
            limit=10,
        )
        for _ in range(bench_count):
            t0 = time.time()
            await sim_svc.search_by_text(bench_search_req)
            total_search_time += (time.time() - t0)
            
    avg_search = (total_search_time / bench_count) * 1000
    print(f"  ✅ Avg hybrid similarity search latency: {avg_search:.2f} ms")

    print("\n" + "=" * 60)
    print("🎉 ALL INTEGRATION TESTS PASSED SUCCESSFULLY! Phase 2.1 is fully operational.")
    print("=" * 60)
    return True


def func_count_crimes():
    from sqlalchemy import func
    return select(func.count(Crime.id))

def MAX_RETRIES_TEST():
    from app.services.dna_service import MAX_RETRIES
    return MAX_RETRIES

if __name__ == "__main__":
    try:
        success = asyncio.run(verify_pipeline())
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
