# Benchmark & Verification Script: FTS Phase 1
import asyncio
import time
import os
import sys

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.services.similarity_service import SimilarityService
from app.schemas.dna import SimilaritySearchRequest

async def run_benchmark():
    print("=========================================")
    print("🚀 RUNNING PHASE 1 HYBRID RETRIEVAL BENCHMARKS")
    print("=========================================")

    async with AsyncSessionLocal() as db:
        service = SimilarityService(db)

        queries = [
            ("English query: ATM robbery", "ATM robbery"),
            ("Kannada query: ದರೋಡೆ (Robbery)", "ದರೋಡೆ"),
            ("Mixed/transliterated query: jewelry theft", "jewelry theft"),
            ("Shorthand abbreviation query: FIR-2026-001 (exact match)", "FIR-2026-001"),
            ("Misspelling query: robery on road", "robery on road"),
        ]

        for desc, query in queries:
            print(f"\nEvaluating: {desc}")
            req = SimilaritySearchRequest(
                query_text=query,
                limit=5,
                min_similarity=0.20,
            )
            
            t0 = time.time()
            res = await service.search_by_text(req)
            latency = (time.time() - t0) * 1000

            print(f"  Latency: {latency:.2f} ms")
            print(f"  Candidates Scanned: {res.total_candidates_scanned}")
            print(f"  Matches Found: {len(res.results)}")
            
            for idx, r in enumerate(res.results[:3]):
                print(f"    [{idx+1}] FIR: {r.fir_number} | Score: {r.similarity_score} | FTS: {r.fts_score} | Semantic: {r.semantic_score}")
                print(f"        Explanation: {r.explanation}")
                print(f"        Matched Terms: {r.matched_terms}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
