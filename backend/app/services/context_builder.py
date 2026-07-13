"""
PAC — Context Builder

Converts trimmed, ranked retrieval data into a clean, structured JSON context
ready for injection into the LLM prompt.  Raw ORM objects, list objects, or
low-level data structures are never passed directly to the LLM.

The output schema is stable so prompt_builder.py can rely on fixed keys.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def build_context(
    intent: str,
    trimmed_context: Dict[str, Any],
    ranked_evidence: List[Dict[str, Any]],
    entity_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Construct a structured, LLM-safe context dict.

    Args:
        intent:          Classified intent (e.g. 'criminal_profile').
        trimmed_context: Ranked and trimmed data from Evidence Ranker.
        ranked_evidence: Flat list of top-N scored evidence items.
        entity_context:  Conversation session entities (criminal_id etc.).

    Returns:
        Structured context dict for injection into the prompt.
    """
    ctx: Dict[str, Any] = {
        "intent": intent,
        "entities": _sanitise_entities(entity_context),
        "crime_summary": {},
        "similar_cases": [],
        "behaviour": {},
        "network": {},
        "geo": {},
        "prediction": {},
        "evidence": [],
        "recommendations": [],
        "data_sources": [],
    }

    # ── DNA / Crime Summary ────────────────────────────────────────────────────
    dna = trimmed_context.get("dna")
    if dna:
        ctx["crime_summary"] = {
            "crime_id": dna.get("crime_id"),
            "crime_method": dna.get("crime_method"),
            "target_type": dna.get("target_type"),
            "escape_method": dna.get("escape_method"),
            "planning_level": dna.get("planning_level"),
            "gang_involved": dna.get("gang_involved"),
            "time_of_day_slot": dna.get("time_of_day_slot"),
            "mo_summary": dna.get("mo_text", "")[:300],  # cap narrative length
        }
        ctx["data_sources"].append("Crime DNA")

    # ── Similar Cases ──────────────────────────────────────────────────────────
    similarity = trimmed_context.get("similarity")
    if similarity:
        ctx["similar_cases"] = [
            {
                "fir_number": r.get("fir_number"),
                "crime_type": r.get("crime_type"),
                "district": r.get("district"),
                "occurred_at": r.get("occurred_at"),
                "similarity_score": r.get("similarity_score"),
                "explanation": r.get("explanation"),
            }
            for r in similarity.get("results", [])
        ]
        ctx["data_sources"].append("Hybrid Similarity Engine")

    # ── Behaviour Profile ──────────────────────────────────────────────────────
    behaviour = trimmed_context.get("behaviour")
    if behaviour:
        ctx["behaviour"] = {
            "risk_level": behaviour.get("risk_level"),
            "risk_score": behaviour.get("risk_score"),
            "profile_summary": behaviour.get("profile_summary"),
            "escalation_trend": behaviour.get("escalation_trend"),
            "violence_score": behaviour.get("violence_score"),
            "gang_affiliation_score": behaviour.get("gang_affiliation_score"),
            "operating_radius_km": behaviour.get("operating_radius_km"),
            "preferred_district": behaviour.get("preferred_district"),
            "preferred_time_slot": behaviour.get("preferred_time_slot"),
            "primary_crime_type": behaviour.get("primary_crime_type"),
        }
        ctx["data_sources"].append("Behaviour Intelligence")

        # Merge behaviour evidence and recommendations
        ctx["evidence"].extend(behaviour.get("evidence", []))
        ctx["recommendations"].extend(behaviour.get("recommendations", []))

    # ── Prediction ─────────────────────────────────────────────────────────────
    prediction = trimmed_context.get("prediction")
    if prediction and isinstance(prediction, dict):
        criminal_risk = prediction.get("criminal_risk")
        district_risk = prediction.get("district_risk")
        gang_threat   = prediction.get("gang_threat")

        if criminal_risk:
            ctx["prediction"]["criminal_risk"] = {
                "risk_level": criminal_risk.get("risk_level"),
                "score": criminal_risk.get("prediction_score"),
                "confidence": criminal_risk.get("confidence"),
                "reason_code": criminal_risk.get("reason_code"),
            }
            ctx["evidence"].extend(criminal_risk.get("evidence", []))
            ctx["recommendations"].extend(criminal_risk.get("recommendations", []))
            ctx["data_sources"].append("Predictive Intelligence")

        if district_risk:
            ctx["prediction"]["district_risk"] = {
                "district": district_risk.get("district"),
                "risk_level": district_risk.get("risk_level"),
                "score": district_risk.get("score"),
            }
            ctx["evidence"].extend(district_risk.get("evidence", []))
            ctx["recommendations"].extend(district_risk.get("recommendations", []))

        if gang_threat:
            ctx["prediction"]["gang_threat"] = {
                "gang_name": gang_threat.get("gang_name"),
                "threat_level": gang_threat.get("threat_level"),
                "score": gang_threat.get("score"),
            }
            ctx["evidence"].extend(gang_threat.get("evidence", []))

    # ── Criminal Network (Neo4j) ───────────────────────────────────────────────
    graph = trimmed_context.get("graph")
    if graph:
        network = graph.get("criminal_network", {})
        gang_members = graph.get("gang_members", [])

        ctx["network"] = {
            "co_offenders": _safe_list(network.get("associates", []), 8),
            "crimes": _safe_list(network.get("crimes", []), 5),
            "gang_members": _safe_list(gang_members, 10),
        }
        ctx["data_sources"].append("Criminal Network Intelligence (Neo4j)")

    # ── Geo Intelligence ───────────────────────────────────────────────────────
    geo = trimmed_context.get("geo")
    if geo:
        ctx["geo"] = {
            "total_hotspots": geo.get("total_hotspots"),
            "district_filter": geo.get("district_filter"),
            "hotspots": [
                {
                    "cluster_id": h.get("cluster_id"),
                    "crime_count": h.get("crime_count"),
                    "dominant_crime_type": h.get("dominant_crime_type"),
                    "peak_time": h.get("peak_time"),
                    "trend": h.get("hotspot_trend"),
                    "risk_level": h.get("risk_level"),
                    "patrol_window": h.get("suggested_patrol_window"),
                    "recommendation": h.get("recommendation"),
                }
                for h in geo.get("hotspots", [])
            ],
        }
        ctx["data_sources"].append("Geo Intelligence")

    # ── Top Ranked Evidence (flat list for easy LLM reading) ──────────────────
    ctx["evidence"].extend([
        item["label"]
        for item in ranked_evidence
        if item["source"] not in ("behaviour", "prediction:criminal_risk")
        and item["label"] not in ctx["evidence"]
    ])

    # Deduplicate evidence list
    seen: set = set()
    unique_evidence: List[str] = []
    for fact in ctx["evidence"]:
        if fact not in seen:
            seen.add(fact)
            unique_evidence.append(fact)
    ctx["evidence"] = unique_evidence

    # Deduplicate data sources
    ctx["data_sources"] = list(dict.fromkeys(ctx["data_sources"]))

    logger.debug(
        f"ContextBuilder: intent={intent}, sources={ctx['data_sources']}, "
        f"evidence_items={len(ctx['evidence'])}"
    )
    return ctx


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sanitise_entities(entity_context: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values and convert UUIDs to strings for JSON safety."""
    return {
        k: str(v)
        for k, v in entity_context.items()
        if v is not None
    }


def _safe_list(items: Any, limit: int) -> List[Any]:
    """Return a safely bounded list from any input."""
    if not isinstance(items, list):
        return []
    return items[:limit]
