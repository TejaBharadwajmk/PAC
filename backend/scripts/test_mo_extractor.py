# Phase 2 — MO Feature Extraction and Scorer Unit Verification

import sys
import os
import time

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.mo_extractor import mo_extractor
from app.services.similarity_service import _score_features, get_mo_feature_weights

def test_mo_extractor():
    print("=========================================")
    print("🚀 RUNNING PHASE 2 MO EXTRACTION VERIFICATION")
    print("=========================================")

    # 1. Test Weapon Extractor (English & Kannada & Mixed)
    test_cases = [
        ("The thief pulled out a dagger at midnight in Bengaluru", 
         {"weapon_used": "knife", "time_of_day_slot": "night", "district": "bengaluru"}),
        
        ("ಆರೋಪಿಯು ಚಾಕು ತೋರಿಸಿ ದರೋಡೆ ಮಾಡಿದ್ದಾನೆ", 
         {"weapon_used": "knife", "crime_type": "robbery"}),
        
        ("gang of 3 broke main door lock of jeweler shop with crowbar and escaped on bike", 
         {"gang_involved": "true", "crime_method": "forced_entry", "entry_method": "front_door", "target_type": "shop", "escape_method": "bike"}),
         
        ("random unknown word test with hack and website links", 
         {"crime_method": "cyber", "entry_method": "online"}),
    ]

    for text, expected in test_cases:
        print(f"\nQuery text: '{text}'")
        features, confidence, matched, unknowns = mo_extractor.extract_query_features(text)
        print(f"  Extracted: {features}")
        print(f"  Confidence: {confidence}")
        print(f"  Matched Keywords: {matched}")
        print(f"  Unknown Tokens: {unknowns[:5]}")
        
        for k, v in expected.items():
            assert features.get(k) == v, f"Expected {k}={v}, got {features.get(k)}"
        print("  ✅ Matches expected mock output")

    # 2. Test MO Scorer (Dynamic weights & redistribution)
    print("\nEvaluating MO Scorer weights & alignment...")
    candidate_profile = {
        "crime_type": "robbery",
        "crime_method": "forced_entry",
        "weapon_used": "knife",
        "entry_method": "front_door",
        "target_type": "shop",
        "escape_method": "bike",
        "time_of_day_slot": "night",
        "gang_involved": True, # Boolean
        "district": "bengaluru",
    }
    
    # Fully matching query features
    query_features_all = {
        "weapon_used": "knife",
        "target_type": "shop",
        "district": "bengaluru",
    }
    score, matched, missing = _score_features(query_features_all, candidate_profile)
    print(f"  All-match query features score: {score} | Matched: {matched} | Missing: {missing}")
    assert score == 1.0, f"Expected score=1.0, got {score}"
    assert len(missing) == 0

    # Partially matching query features (1 match, 1 mismatch)
    query_features_part = {
        "weapon_used": "knife",        # match
        "target_type": "residence",   # mismatch
    }
    score_p, matched_p, missing_p = _score_features(query_features_part, candidate_profile)
    print(f"  Partial-match query features score: {score_p} | Matched: {matched_p} | Missing: {missing_p}")
    assert score_p < 1.0 and score_p > 0.0
    assert "target_type" in missing_p

    # Empty query features (redistribution mode)
    score_e, matched_e, missing_e = _score_features({}, candidate_profile)
    print(f"  Empty query features (None score): {score_e}")
    assert score_e is None

    # 3. Benchmark latency overhead of Extraction Engine
    print("\nBenchmarking Synonym Extraction Engine speed...")
    t0 = time.time()
    iters = 1000
    for _ in range(iters):
        mo_extractor.extract_query_features("Two suspects broke main door lock of jeweler shop with crowbar at midnight and escaped on bike in Bangalore")
    avg_latency = ((time.time() - t0) / iters) * 1000
    print(f"  Average Extraction Latency: {avg_latency:.4f} ms")
    assert avg_latency < 10.0, f"Target <10ms failed, average latency was {avg_latency:.2f}ms"
    print("  ✅ Extraction latency satisfies KSP efficiency constraint (< 10 ms)")

if __name__ == "__main__":
    test_mo_extractor()
