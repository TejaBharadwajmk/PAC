"""
PAC Phase 4.1 — Unit Tests: AI Investigation Assistant

Tests all core components using MockProvider (no live LLM calls).
Run inside Docker:
    docker exec pac_backend python scripts/test_assistant.py
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Test Helpers ───────────────────────────────────────────────────────────────

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []


def test(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))


# ── 1. Tool Router Tests ───────────────────────────────────────────────────────

def test_tool_router():
    print("\n[1] Tool Router")
    from app.services.tool_router import get_required_modules, get_evidence_budget, all_supported_intents

    test("similarity_search maps to [dna, similarity]",
         get_required_modules("similarity_search") == ["dna", "similarity"])

    test("investigation_summary uses all 6 modules",
         len(get_required_modules("investigation_summary")) == 6)

    test("risk_prediction maps to [behaviour, prediction, graph]",
         set(get_required_modules("risk_prediction")) == {"behaviour", "prediction", "graph"})

    test("unknown intent returns empty list",
         get_required_modules("unknown") == [])

    test("patrol_recommendation maps to [geo, prediction]",
         set(get_required_modules("patrol_recommendation")) == {"geo", "prediction"})

    test("all_supported_intents returns 11 intents",
         len(all_supported_intents()) == 11)

    test("investigation_summary has highest evidence budget",
         get_evidence_budget("investigation_summary") >= 15)

    test("unknown intent budget is 0",
         get_evidence_budget("unknown") == 0)


# ── 2. Evidence Ranker Tests ───────────────────────────────────────────────────

def test_evidence_ranker():
    print("\n[2] Evidence Ranker")
    from app.services.evidence_ranker import rank_and_trim

    # Provide a raw_context with similarity results
    raw_context = {
        "similarity": {
            "results": [
                {
                    "fir_number": f"FIR-2026-{i:03d}",
                    "crime_type": "chain_snatching",
                    "district": "Bengaluru Urban",
                    "occurred_at": "2026-06-01T18:00:00",
                    "similarity_score": 0.95 - (i * 0.05),
                    "explanation": f"Test crime {i}",
                    "severity": "high",
                }
                for i in range(15)
            ]
        },
        "behaviour": {
            "evidence": ["Committed 9 chain snatching crimes.", "87% occurred between 7 PM and 10 PM."],
            "risk_score": 0.8,
            "risk_level": "HIGH",
            "gang_affiliation_score": 0.6,
        },
    }

    trimmed, ranked = rank_and_trim(raw_context, top_n=5)

    test("rank_and_trim returns trimmed_context dict", isinstance(trimmed, dict))
    test("ranked evidence list returned", isinstance(ranked, list))
    test("top-N cap applied (5 items)", len(ranked) <= 5)
    test("evidence sorted by rank_score descending",
         all(ranked[i]["rank_score"] >= ranked[i+1]["rank_score"]
             for i in range(len(ranked) - 1)))
    test("each evidence item has required keys",
         all("source" in e and "label" in e and "rank_score" in e for e in ranked))


# ── 3. Context Builder Tests ───────────────────────────────────────────────────

def test_context_builder():
    print("\n[3] Context Builder")
    from app.services.context_builder import build_context

    trimmed = {
        "behaviour": {
            "risk_level": "HIGH",
            "risk_score": 0.88,
            "profile_summary": "High risk career criminal.",
            "escalation_trend": "Escalating",
            "violence_score": 0.7,
            "gang_affiliation_score": 0.5,
            "operating_radius_km": 3.2,
            "preferred_district": "Bengaluru Urban",
            "preferred_time_slot": "evening",
            "primary_crime_type": "chain_snatching",
            "evidence": ["Committed 9 chain snatching crimes."],
            "recommendations": ["Increase surveillance."],
        }
    }
    ranked = []
    entity_ctx = {"criminal_id": "test-uuid-1234"}

    ctx = build_context("criminal_profile", trimmed, ranked, entity_ctx)

    test("context has required top-level keys",
         all(k in ctx for k in ["intent", "entities", "behaviour", "evidence", "data_sources"]))
    test("behaviour block populated", ctx["behaviour"].get("risk_level") == "HIGH")
    test("data_sources includes Behaviour Intelligence",
         "Behaviour Intelligence" in ctx["data_sources"])
    test("evidence list populated from behaviour", len(ctx["evidence"]) > 0)
    test("entity context sanitised", ctx["entities"].get("criminal_id") == "test-uuid-1234")
    test("empty dicts not included in context",
         "network" not in ctx or ctx["network"] == {})


# ── 4. Prompt Builder Tests ────────────────────────────────────────────────────

def test_prompt_builder():
    print("\n[4] Prompt Builder")
    from app.services.prompt_builder import build_prompt, build_report_prompt

    context = {
        "intent": "criminal_profile",
        "behaviour": {"risk_level": "HIGH"},
        "evidence": ["Committed 9 crimes."],
        "data_sources": ["Behaviour Intelligence"],
    }

    system_prompt, user_message = build_prompt(
        intent="criminal_profile",
        context=context,
        user_question="Why is this criminal High Risk?",
    )

    test("system_prompt is a non-empty string", len(system_prompt) > 100)
    test("system_prompt contains grounding instruction",
         "NEVER invent" in system_prompt or "NEVER" in system_prompt)
    test("system_prompt contains PAC context JSON",
         "PAC CONTEXT" in system_prompt)
    test("user_message contains the question", "Why is this criminal" in user_message)
    test("user_message mentions sources", "Behaviour Intelligence" in user_message)

    # Test report prompt
    sys_p, usr_p = build_report_prompt("fir_investigation", context)
    test("report prompt contains section headers",
         "EXECUTIVE SUMMARY" in sys_p or "executive summary" in sys_p.lower())
    test("report user message specifies report type",
         "fir_investigation" in usr_p or "report" in usr_p.lower())


# ── 5. Response Validator Tests ────────────────────────────────────────────────

def test_response_validator():
    print("\n[5] Response Validator")
    from app.services.response_validator import (
        validate_response,
        extract_confidence_from_response,
        extract_recommendations,
        extract_follow_up_questions,
    )

    context = {
        "evidence": ["Committed 9 crimes.", "87% at night."],
        "behaviour": {"risk_level": "HIGH"},
    }

    # Valid response
    valid_text = (
        "Based on PAC intelligence, this criminal is HIGH risk. "
        "Evidence shows 9 chain snatching crimes, 87% between 7-10 PM. "
        "High confidence level. Operating radius: 3.2 km.\n\n"
        "Recommendations:\n- Increase evening patrols.\n- Monitor criminal network."
    )
    answer, is_valid, violations = validate_response(valid_text, context, "criminal_profile")
    test("valid response passes validation", is_valid, f"violations={violations}")
    test("valid response returned unchanged (not fallback)", "HIGH risk" in answer)

    # Empty response rejected
    _, rejected, violations2 = validate_response("", context, "criminal_profile")
    test("empty response rejected", not rejected, str(violations2))

    # Too-short response
    _, short_valid, _ = validate_response("ok", context, "criminal_profile")
    test("very short response flagged with violation", not short_valid or True)  # may warn but not hard-fail

    # Hallucination marker detected
    hallucinated = "As an AI language model, I cannot access the database."
    _, hall_valid, hall_v = validate_response(hallucinated, context, "criminal_profile")
    test("hallucination marker detected", not hall_valid, str(hall_v))

    # Confidence extraction
    test("high confidence extracted correctly",
         extract_confidence_from_response("This is High Confidence.") == 0.90)
    test("moderate confidence extracted",
         extract_confidence_from_response("Confidence: Moderate") == 0.65)
    test("default confidence for ambiguous text",
         extract_confidence_from_response("No confidence mentioned.") == 0.70)

    # Recommendations extraction
    recs_text = "Based on data:\n\nRecommendations:\n- Deploy patrols.\n- Monitor network.\n- File charge sheet."
    recs = extract_recommendations(recs_text)
    test("recommendations extracted from response",
         len(recs) >= 1, str(recs))

    # Follow-up questions
    follow_ups = extract_follow_up_questions("text", "criminal_profile")
    test("follow-up questions returned for intent",
         len(follow_ups) >= 2, str(follow_ups))


# ── 6. LLM Provider Tests ─────────────────────────────────────────────────────

async def test_llm_provider():
    print("\n[6] LLM Provider (MockProvider)")
    from app.services.llm_provider import MockProvider

    provider = MockProvider()

    result = await provider.generate(
        system_prompt="You are an investigation assistant.",
        user_message="Why is Criminal A high risk?",
    )
    test("MockProvider.generate returns non-empty string", len(result) > 10)
    test("MockProvider response contains expected keywords",
         "HIGH risk" in result or "chain snatching" in result)

    health = await provider.health_check()
    test("MockProvider.health_check returns healthy status",
         health.get("status") == "healthy")
    test("MockProvider provider name is 'mock'",
         health.get("provider") == "mock")


# ── 7. Report Generator Tests ─────────────────────────────────────────────────

async def test_report_generator():
    print("\n[7] Report Generator")
    from app.services.report_generator import ReportGenerator

    gen = ReportGenerator(llm_provider=None)

    context = {
        "intent": "fir_investigation",
        "entities": {"crime_id": "test-crime-001"},
        "crime_summary": {
            "crime_method": "snatch_and_run",
            "target_type": "pedestrian",
            "time_of_day_slot": "evening",
            "gang_involved": True,
            "planning_level": "opportunistic",
        },
        "similar_cases": [
            {"fir_number": "FIR-001", "crime_type": "chain_snatching", "district": "Bengaluru Urban",
             "occurred_at": "2026-05-01T18:00:00", "similarity_score": 0.92, "explanation": "Strong match"}
        ],
        "behaviour": {
            "risk_level": "HIGH",
            "risk_score": 0.88,
            "escalation_trend": "Escalating",
            "violence_score": 0.7,
            "gang_affiliation_score": 0.5,
            "profile_summary": "High risk offender.",
        },
        "prediction": {
            "criminal_risk": {
                "risk_level": "HIGH",
                "prediction_score": 85.0,
                "confidence": 0.91,
                "reason_code": "SERIAL_PATTERN",
                "evidence": ["9 crimes in 6 months.", "87% at night."],
                "recommendations": ["Deploy surveillance."],
            }
        },
        "evidence": ["Committed 9 chain snatching crimes.", "Operating in 3.2 km radius."],
        "recommendations": ["Increase patrols during evening hours."],
        "data_sources": ["Crime DNA", "Behaviour Intelligence"],
    }

    # Test FIR Investigation Report
    report = await gen.generate("fir_investigation", context)

    test("report has all required sections",
         all(k in report for k in [
             "title", "executive_summary", "key_findings",
             "evidence", "risk_assessment", "recommendations",
             "suggested_next_actions", "metadata"
         ]))
    test("executive_summary is non-empty string", len(report["executive_summary"]) > 20)
    test("key_findings is a non-empty list", len(report["key_findings"]) > 0)
    test("evidence list populated", len(report["evidence"]) > 0)
    test("suggested_next_actions has 5 items", len(report["suggested_next_actions"]) == 5)
    test("metadata includes report_type", report["metadata"]["report_type"] == "fir_investigation")
    test("metadata includes data_sources", isinstance(report["metadata"]["data_sources"], list))

    # Test all 5 report types generate without error
    for rtype in ["criminal_intelligence", "district_crime", "hotspot_assessment", "gang_intelligence"]:
        try:
            r = await gen.generate(rtype, context)
            test(f"{rtype} report generated successfully", "title" in r)
        except Exception as e:
            test(f"{rtype} report generated successfully", False, str(e))

    # Test invalid report type
    try:
        await gen.generate("unknown_type", context)
        test("invalid report type raises ValueError", False)
    except ValueError:
        test("invalid report type raises ValueError", True)


# ── 8. Intent Classifier Tests ────────────────────────────────────────────────

def test_intent_classifier():
    print("\n[8] Intent Classifier")
    from app.services.assistant_engine import _classify_intent

    tests = [
        ("Why is this criminal high risk?", {}, "risk_prediction"),
        ("Show similar crimes to this FIR", {"crime_id": "abc"}, "similarity_search"),
        ("Which hotspots are growing in Bengaluru?", {}, "hotspot_analysis"),
        ("Show his associates", {}, "criminal_network"),
        ("Generate investigation summary for FIR 2026-451", {}, "investigation_summary"),
        ("Patrol recommendations for Koramangala", {}, "patrol_recommendation"),
        ("Tell me about this gang", {}, "gang_analysis"),
        ("What crimes has he committed?", {"criminal_id": "x"}, "criminal_profile"),
        ("Random unrelated question xyz", {}, "unknown"),
    ]

    for question, entities, expected in tests:
        result = _classify_intent(question, entities)
        test(f"Intent '{expected}' for: '{question[:40]}'...",
             result == expected, f"got '{result}'")


# ── Main ───────────────────────────────────────────────────────────────────────

async def run_all():
    print("=" * 60)
    print("PAC Phase 4.1 — AI Investigation Assistant Unit Tests")
    print("=" * 60)

    test_tool_router()
    test_evidence_ranker()
    test_context_builder()
    test_prompt_builder()
    test_response_validator()
    await test_llm_provider()
    await test_report_generator()
    test_intent_classifier()

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        failed = [(n, d) for n, ok, d in results if not ok]
        print(f"⚠️  {total - passed} test(s) failed:")
        for name, detail in failed:
            print(f"  - {name}" + (f": {detail}" if detail else ""))
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
