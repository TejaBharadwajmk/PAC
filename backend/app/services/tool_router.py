"""
PAC — Tool Router

Maps each classified intent to the exact set of PAC intelligence modules
required for retrieval.  The Retriever Service uses this map to call
only the necessary services — reducing latency and LLM token usage.

TOOL_MAP is the single source of truth for all intent → module bindings.
Adding a new intent requires only adding one entry here.
"""

from typing import Dict, List


# ── Intent → Module Mapping ────────────────────────────────────────────────────
# Each value is an ordered list of module keys the retriever will invoke.
# Keys match the handler methods inside RetrieverService.

TOOL_MAP: Dict[str, List[str]] = {
    # Crime similarity: DNA + vector search only
    "similarity_search": ["dna", "similarity"],

    # Criminal behaviour: behaviour profile + risk forecast
    "criminal_profile": ["behaviour", "prediction"],

    # Criminal network: Neo4j graph only
    "criminal_network": ["graph"],

    # Hotspot evolution: geo clusters + growth forecasts
    "hotspot_analysis": ["geo", "prediction"],

    # District crime trends: geo + district risk index
    "district_analysis": ["geo", "prediction"],

    # Gang threat: Neo4j gang data + gang threat score
    "gang_analysis": ["graph", "prediction"],

    # Risk explanation: behaviour profile + prediction + network context
    "risk_prediction": ["behaviour", "prediction", "graph"],

    # Full investigation brief: every available module
    "investigation_summary": ["dna", "similarity", "behaviour", "prediction", "graph", "geo"],

    # Patrol guidance: geo hotspots + district risk
    "patrol_recommendation": ["geo", "prediction"],

    # Side-by-side comparison of two criminals
    "compare_entities": ["behaviour", "prediction", "graph"],

    # Graceful fallback — no retrieval attempted
    "unknown": [],
}


def get_required_modules(intent: str) -> List[str]:
    """Returns the ordered list of PAC module keys for a given intent.

    Args:
        intent: Classified intent string (e.g. 'criminal_profile').

    Returns:
        List of module keys, empty list for unknown intents.
    """
    return TOOL_MAP.get(intent, [])


def all_supported_intents() -> List[str]:
    """Returns all registered intent names (for health checks and docs)."""
    return list(TOOL_MAP.keys())


# ── Evidence Token Budget per Intent ──────────────────────────────────────────
# Controls how many ranked evidence items the Evidence Ranker passes to the LLM.
# High-context intents (investigation_summary) allow more evidence.

EVIDENCE_BUDGET: Dict[str, int] = {
    "similarity_search":     8,
    "criminal_profile":      10,
    "criminal_network":      8,
    "hotspot_analysis":      8,
    "district_analysis":     8,
    "gang_analysis":         8,
    "risk_prediction":       12,
    "investigation_summary": 15,
    "patrol_recommendation": 8,
    "compare_entities":      12,
    "unknown":               0,
}


def get_evidence_budget(intent: str) -> int:
    """Returns the maximum evidence items to pass to the LLM for this intent."""
    return EVIDENCE_BUDGET.get(intent, 10)
