"""
PAC Phase 4.1 — E2E Verification: AI Investigation Assistant

Full pipeline end-to-end test. Uses MockProvider so no live LLM required.
Run inside Docker:
    docker exec pac_backend python scripts/verify_assistant_e2e.py
"""

import asyncio
import sys
import os
import time
import json
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


PASS = "✅"
FAIL = "❌"
results = []


def test(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))


# ── Force MockProvider for E2E tests ──────────────────────────────────────────
os.environ["LLM_PROVIDER"] = "mock"

# ── DB Session Mock ────────────────────────────────────────────────────────────
class MockDB:
    """Minimal mock that satisfies retriever_service's async session interface."""
    async def execute(self, *args, **kwargs):
        class Result:
            def scalar_one_or_none(self): return None
            def scalars(self):
                class Scalars:
                    def all(self): return []
                return Scalars()
        return Result()


# ── 1. Intent Classification E2E ──────────────────────────────────────────────

def test_intent_pipeline():
    print("\n[1] Intent Classification Pipeline")
    from app.services.assistant_engine import _classify_intent

    test_cases = [
        ("Generate investigation briefing for FIR 2026-451", {}, "investigation_summary"),
        ("Show me crimes similar to FIR-2026-001", {"crime_id": "abc"}, "similarity_search"),
        ("Why is this criminal classified as High Risk?", {"criminal_id": "xyz"}, "risk_prediction"),
        ("Which hotspots are growing in Bengaluru Urban?", {}, "hotspot_analysis"),
        ("What patrols should we deploy in Koramangala?", {}, "patrol_recommendation"),
        ("Show criminal network and associates", {"criminal_id": "xyz"}, "criminal_network"),
        ("District crime analysis for Mysuru", {}, "district_analysis"),
        ("What is the gang threat for Black Eagles?", {}, "gang_analysis"),
    ]

    for question, entities, expected in test_cases:
        intent = _classify_intent(question, entities)
        test(f"Q: '{question[:45]}'", intent == expected, f"expected={expected}, got={intent}")


# ── 2. Tool Router → Module Selection ─────────────────────────────────────────

def test_tool_routing():
    print("\n[2] Tool Router → Module Selection")
    from app.services.tool_router import get_required_modules, get_evidence_budget

    expectations = {
        "similarity_search":     (["dna", "similarity"], 8),
        "criminal_profile":      (["behaviour", "prediction"], 10),
        "investigation_summary": (6, 15),  # (count, budget)
        "patrol_recommendation": (["geo", "prediction"], 8),
        "unknown":               ([], 0),
    }

    for intent, (expected_modules, expected_budget) in expectations.items():
        modules = get_required_modules(intent)
        budget = get_evidence_budget(intent)

        if isinstance(expected_modules, int):
            test(f"{intent}: correct module count ({expected_modules})", len(modules) == expected_modules)
        else:
            test(f"{intent}: correct modules", set(modules) == set(expected_modules), str(modules))

        test(f"{intent}: correct evidence budget ({expected_budget})", budget == expected_budget)


# ── 3. Evidence Ranker Pipeline ────────────────────────────────────────────────

def test_evidence_ranker_pipeline():
    print("\n[3] Evidence Ranker Pipeline")
    from app.services.evidence_ranker import rank_and_trim

    # Build a realistic raw_context
    raw = {
        "similarity": {
            "results": [
                {
                    "fir_number": f"FIR-{i:04d}",
                    "crime_type": "chain_snatching",
                    "district": "Bengaluru Urban",
                    "occurred_at": f"2026-0{(i % 6) + 1}-15T19:00:00",
                    "similarity_score": 0.95 - (i * 0.04),
                    "explanation": f"Strong match {i}",
                    "severity": "high" if i < 5 else "medium",
                }
                for i in range(20)
            ]
        },
        "behaviour": {
            "evidence": [
                "Committed 9 chain snatching crimes.",
                "87% of offences between 19:00-22:00.",
                "Operating radius limited to 3.2 km.",
            ],
            "risk_score": 0.88,
            "risk_level": "HIGH",
            "gang_affiliation_score": 0.65,
        },
        "prediction": {
            "criminal_risk": {
                "risk_level": "HIGH",
                "confidence": 0.91,
                "score": 85.0,
                "evidence": ["Recidivism score is 0.8.", "Gang influence score is 0.65."],
                "recommendations": ["Deploy surveillance."],
            }
        }
    }

    t0 = time.monotonic()
    trimmed, ranked = rank_and_trim(raw, top_n=10)
    elapsed = (time.monotonic() - t0) * 1000

    test("Ranking completed", isinstance(ranked, list))
    test(f"Top-10 cap applied", len(ranked) <= 10, f"got {len(ranked)}")
    test("Evidence sorted descending by rank_score",
         all(ranked[i]["rank_score"] >= ranked[i+1]["rank_score"]
             for i in range(len(ranked) - 1) if len(ranked) > 1))
    test("Similarity results trimmed in context",
         len(trimmed.get("similarity", {}).get("results", [])) <= 10)
    test(f"Ranking latency < 50ms", elapsed < 50, f"{elapsed:.1f}ms")


# ── 4. Context Builder Pipeline ───────────────────────────────────────────────

def test_context_builder_pipeline():
    print("\n[4] Context Builder Pipeline")
    from app.services.context_builder import build_context
    from app.services.evidence_ranker import rank_and_trim

    raw = {
        "dna": {
            "crime_id": "test-crime-001",
            "crime_method": "snatch_and_run",
            "target_type": "pedestrian",
            "escape_method": "motorcycle",
            "planning_level": "opportunistic",
            "gang_involved": True,
            "time_of_day_slot": "evening",
        },
        "behaviour": {
            "risk_level": "HIGH",
            "risk_score": 0.88,
            "profile_summary": "High risk career offender.",
            "escalation_trend": "Escalating",
            "violence_score": 0.7,
            "gang_affiliation_score": 0.65,
            "operating_radius_km": 3.2,
            "preferred_district": "Bengaluru Urban",
            "preferred_time_slot": "evening",
            "primary_crime_type": "chain_snatching",
            "evidence": ["Committed 9 crimes.", "87% at night."],
            "recommendations": ["Increase surveillance."],
        },
        "geo": {
            "total_hotspots": 3,
            "district_filter": "Bengaluru Urban",
            "hotspots": [
                {
                    "cluster_id": 1,
                    "crime_count": 12,
                    "dominant_crime_type": "chain_snatching",
                    "peak_time": "evening",
                    "hotspot_trend": "Emerging",
                    "risk_level": "High",
                    "confidence_score": 0.85,
                    "suggested_patrol_window": "17:30-22:30",
                    "recommendation": "Deploy patrol units.",
                }
            ],
        },
    }

    trimmed, ranked = rank_and_trim(raw, top_n=10)
    ctx = build_context(
        intent="investigation_summary",
        trimmed_context=trimmed,
        ranked_evidence=ranked,
        entity_context={"criminal_id": "test-criminal-001", "crime_id": "test-crime-001"},
    )

    required_keys = ["intent", "entities", "crime_summary", "behaviour", "geo", "evidence", "data_sources"]
    test("Context has all required keys", all(k in ctx for k in required_keys))
    test("Crime summary populated", ctx["crime_summary"].get("crime_method") == "snatch_and_run")
    test("Behaviour block populated", ctx["behaviour"].get("risk_level") == "HIGH")
    test("Geo block populated", len(ctx["geo"].get("hotspots", [])) > 0)
    test("Evidence list non-empty", len(ctx["evidence"]) > 0)
    test("Data sources list populated", len(ctx["data_sources"]) > 0)
    test("Evidence deduplicated", len(ctx["evidence"]) == len(set(ctx["evidence"])))


# ── 5. Full Pipeline E2E with MockDB ──────────────────────────────────────────

async def test_full_pipeline():
    print("\n[5] Full Pipeline E2E (MockProvider + MockDB)")
    from app.services.tool_router import get_required_modules
    from app.services.evidence_ranker import rank_and_trim
    from app.services.context_builder import build_context
    from app.services.prompt_builder import build_prompt
    from app.services.response_validator import validate_response, extract_confidence_from_response
    from app.services.llm_provider import MockProvider
    from app.services.assistant_engine import _classify_intent

    question = "Why is this criminal classified as High Risk?"
    entity_context = {"criminal_id": "test-crim-001", "query_text": question}

    # Step 1: Intent
    t_start = time.monotonic()
    intent = _classify_intent(question, entity_context)
    test("Step 1: Intent classified", intent == "risk_prediction", f"intent={intent}")

    # Step 2: Tool routing
    modules = get_required_modules(intent)
    test("Step 2: Modules selected", set(modules) == {"behaviour", "prediction", "graph"})

    # Step 3: Simulated retrieval (mock data, no real DB)
    raw_context = {
        "behaviour": {
            "risk_level": "HIGH",
            "risk_score": 0.88,
            "profile_summary": "High risk career offender.",
            "escalation_trend": "Escalating",
            "violence_score": 0.7,
            "gang_affiliation_score": 0.65,
            "operating_radius_km": 3.2,
            "preferred_district": "Bengaluru Urban",
            "preferred_time_slot": "evening",
            "primary_crime_type": "chain_snatching",
            "evidence": [
                "Committed 9 chain snatching crimes.",
                "87% occurred between 19:00-22:00.",
                "Operating radius limited to 3.2 km.",
                "Associated with Gang X in 6 incidents.",
            ],
            "recommendations": [
                "Deploy evening surveillance in operating district.",
                "Coordinate arrest operation with DCRB.",
            ],
        },
        "prediction": {
            "criminal_risk": {
                "risk_level": "HIGH",
                "prediction_score": 85.0,
                "confidence": 0.91,
                "reason_code": "SERIAL_PATTERN",
                "evidence": ["Recidivism score is 0.8.", "9 crimes in 6 months."],
                "recommendations": ["Initiate targeted surveillance."],
                "score_breakdown": {"crime_severity": 0.7, "recency": 0.8},
            }
        }
    }
    test("Step 3: Raw context assembled", len(raw_context) == 2)

    # Step 4: Evidence ranking
    trimmed, ranked = rank_and_trim(raw_context, top_n=12)
    test("Step 4: Evidence ranked", len(ranked) >= 1)

    # Step 5: Context building
    ctx = build_context(intent, trimmed, ranked, entity_context)
    test("Step 5: Context built with correct intent", ctx["intent"] == "risk_prediction")

    # Step 6: Prompt building
    system_prompt, user_message = build_prompt(intent, ctx, question)
    test("Step 6: System prompt contains grounding rule",
         "NEVER" in system_prompt)
    test("Step 6: User message contains question",
         question[:20] in user_message)

    # Step 7: LLM generation (Mock)
    llm = MockProvider()
    answer = await llm.generate(system_prompt, user_message, ctx)
    test("Step 7: LLM returned non-empty answer", len(answer) > 20)

    # Step 8: Response validation
    validated, is_valid, violations = validate_response(answer, ctx, intent)
    test("Step 8: Response validated", is_valid, str(violations))

    # Step 9: Confidence extraction
    confidence = extract_confidence_from_response(validated)
    test("Step 9: Confidence extracted", 0.0 <= confidence <= 1.0, f"{confidence}")

    t_elapsed = (time.monotonic() - t_start) * 1000
    test(f"Full pipeline latency < 200ms", t_elapsed < 200, f"{t_elapsed:.1f}ms")


# ── 6. Multi-Turn Conversation ────────────────────────────────────────────────

def test_session_memory():
    print("\n[6] Multi-Turn Conversation Memory")
    from app.services.assistant_engine import _resolve_entity_context, _update_session

    session_id = "test-session-e2e"

    # First turn: sets criminal_id
    ctx1 = _resolve_entity_context(
        session_id=session_id,
        question="Show criminal profile for this criminal.",
        criminal_id="criminal-abc-001",
        crime_id=None,
        district=None,
        gang_name=None,
    )
    _update_session(session_id, ctx1)

    # Second turn: follow-up without explicit criminal_id
    ctx2 = _resolve_entity_context(
        session_id=session_id,
        question="Show his associates.",
        criminal_id=None,
        crime_id=None,
        district=None,
        gang_name=None,
    )

    test("First turn sets criminal_id", ctx1["criminal_id"] == "criminal-abc-001")
    test("Second turn inherits criminal_id from session", ctx2["criminal_id"] == "criminal-abc-001")

    # Third turn: override with new criminal
    ctx3 = _resolve_entity_context(
        session_id=session_id,
        question="Now show Criminal B's profile.",
        criminal_id="criminal-xyz-002",
        crime_id=None,
        district=None,
        gang_name=None,
    )
    test("Explicit criminal_id overrides session", ctx3["criminal_id"] == "criminal-xyz-002")


# ── 7. Report Generator E2E ───────────────────────────────────────────────────

async def test_report_e2e():
    print("\n[7] Report Generator E2E (all 5 types)")
    from app.services.report_generator import ReportGenerator

    gen = ReportGenerator()

    context = {
        "intent": "investigation_summary",
        "entities": {"crime_id": "test-001", "district": "Bengaluru Urban"},
        "crime_summary": {
            "crime_method": "snatch_and_run",
            "target_type": "pedestrian",
            "escape_method": "motorcycle",
            "planning_level": "opportunistic",
            "gang_involved": True,
            "time_of_day_slot": "evening",
        },
        "similar_cases": [
            {"fir_number": "FIR-0001", "crime_type": "chain_snatching",
             "district": "Bengaluru Urban", "occurred_at": "2026-05-01T18:00:00",
             "similarity_score": 0.92, "explanation": "Strong semantic match."}
        ],
        "behaviour": {
            "risk_level": "HIGH",
            "risk_score": 0.88,
            "escalation_trend": "Escalating",
            "violence_score": 0.7,
            "gang_affiliation_score": 0.5,
            "operating_radius_km": 3.2,
            "preferred_district": "Bengaluru Urban",
            "profile_summary": "High risk career offender.",
            "evidence": ["9 crimes in 6 months.", "87% at night."],
        },
        "prediction": {
            "criminal_risk": {
                "risk_level": "HIGH",
                "prediction_score": 85.0,
                "confidence": 0.91,
                "reason_code": "SERIAL_PATTERN",
                "evidence": ["Recidivism score is 0.8."],
                "recommendations": ["Deploy surveillance."],
            },
            "district_risk": {
                "district": "Bengaluru Urban",
                "risk_level": "HIGH",
                "score": 78.0,
                "evidence": ["3 active hotspots."],
                "recommendations": ["Increase patrol density."],
            },
            "gang_threat": {
                "gang_name": "Black Eagles",
                "threat_level": "HIGH",
                "score": 82.0,
                "evidence": ["12 members active."],
                "recommendations": ["Initiate network disruption."],
            }
        },
        "network": {
            "co_offenders": [{"name": "Raju", "association_strength": 0.92}],
            "gang_members": [{"name": "Suresh", "risk_score": 0.75}],
        },
        "geo": {
            "total_hotspots": 3,
            "district_filter": "Bengaluru Urban",
            "hotspots": [
                {"cluster_id": 1, "crime_count": 12, "dominant_crime_type": "chain_snatching",
                 "peak_time": "evening", "trend": "Emerging", "risk_level": "High",
                 "patrol_window": "17:30-22:30", "recommendation": "Deploy patrols."}
            ],
        },
        "evidence": ["9 crimes in 6 months.", "87% at night.", "3.2 km operating radius."],
        "recommendations": ["Increase patrols.", "Deploy surveillance."],
        "data_sources": ["Crime DNA", "Behaviour Intelligence", "Predictive Intelligence"],
    }

    required_sections = [
        "title", "executive_summary", "key_findings",
        "evidence", "risk_assessment", "recommendations",
        "suggested_next_actions", "metadata"
    ]

    report_types = [
        "fir_investigation",
        "criminal_intelligence",
        "district_crime",
        "hotspot_assessment",
        "gang_intelligence",
    ]

    latencies = []
    for rtype in report_types:
        t0 = time.monotonic()
        try:
            report = await gen.generate(rtype, context)
            elapsed = (time.monotonic() - t0) * 1000
            latencies.append(elapsed)
            test(f"Report '{rtype}' has all sections",
                 all(k in report for k in required_sections))
            test(f"Report '{rtype}' has non-empty executive summary",
                 len(report.get("executive_summary", "")) > 20)
            test(f"Report '{rtype}' generated in < 100ms", elapsed < 100, f"{elapsed:.1f}ms")
        except Exception as e:
            test(f"Report '{rtype}' generation", False, str(e))

    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"\n  📊 Average report generation: {avg:.1f}ms")


# ── 8. API Schema Validation ───────────────────────────────────────────────────

def test_api_schemas():
    print("\n[8] API Schema Validation")
    from app.schemas.assistant import (
        AssistantChatRequest,
        AssistantChatResponse,
        ReportRequest,
        ReportResponse,
    )

    # Chat request validation
    req = AssistantChatRequest(
        question="Show similar crimes to FIR-2026-001",
        session_id="test-session",
        crime_id="550e8400-e29b-41d4-a716-446655440000",
    )
    test("AssistantChatRequest validates correctly", req.question.startswith("Show"))
    test("session_id preserved", req.session_id == "test-session")

    # Invalid request (too short question)
    try:
        AssistantChatRequest(question="Hi")
        test("Short question raises ValidationError", False)
    except Exception:
        test("Short question raises ValidationError", True)

    # Report request
    rreq = ReportRequest(
        report_type="fir_investigation",
        crime_id="550e8400-e29b-41d4-a716-446655440000",
    )
    test("ReportRequest validates correctly", rreq.report_type == "fir_investigation")

    # Response model
    resp = AssistantChatResponse(
        answer="The criminal is HIGH risk based on 9 recorded offences.",
        confidence=0.91,
        intent="criminal_profile",
        sources=["Behaviour Intelligence", "Predictive Intelligence"],
        evidence=["9 crimes in 6 months."],
        recommendations=["Deploy surveillance."],
        follow_up_questions=["Show his associates?"],
        session_id="test-session",
        is_grounded=True,
        latency_ms=42.5,
    )
    test("AssistantChatResponse has correct confidence", resp.confidence == 0.91)
    test("AssistantChatResponse is_grounded True", resp.is_grounded is True)


# ── Main ───────────────────────────────────────────────────────────────────────

async def run_all():
    print("=" * 65)
    print("PAC Phase 4.1 — AI Investigation Assistant E2E Verification")
    print("=" * 65)
    t_all = time.monotonic()

    test_intent_pipeline()
    test_tool_routing()
    test_evidence_ranker_pipeline()
    test_context_builder_pipeline()
    await test_full_pipeline()
    test_session_memory()
    await test_report_e2e()
    test_api_schemas()

    total_elapsed = (time.monotonic() - t_all) * 1000

    print("\n" + "=" * 65)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed | Total time: {total_elapsed:.0f}ms")

    if passed == total:
        print("🎉 All E2E tests passed! Phase 4.1 is ready for deployment.")
    else:
        failed = [(n, d) for n, ok, d in results if not ok]
        print(f"⚠️  {total - passed} test(s) failed:")
        for name, detail in failed:
            print(f"  - {name}" + (f": {detail}" if detail else ""))

    print("=" * 65)
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
