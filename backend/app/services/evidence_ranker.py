"""
PAC — Evidence Ranker

Ranks and trims raw retrieval results before passing them to the
Context Builder.  Prevents token overflow and keeps the LLM context
focused on the most relevant, high-confidence evidence.

Ranking Formula (per evidence item):
    score = (similarity_score   × 0.30)
           + (prediction_confidence × 0.25)
           + (recency_score         × 0.20)
           + (severity_score        × 0.15)
           + (graph_strength        × 0.10)

All inputs are normalised to [0.0, 1.0] before scoring.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Ranking Weights ────────────────────────────────────────────────────────────
WEIGHTS = {
    "similarity_score":      0.30,
    "prediction_confidence": 0.25,
    "recency_score":         0.20,
    "severity_score":        0.15,
    "graph_strength":        0.10,
}

# Crime severity → numeric weight
SEVERITY_MAP = {
    "critical": 1.0,
    "high":     0.8,
    "medium":   0.6,
    "low":      0.3,
    "unknown":  0.4,
}

# Maximum days for recency normalisation (older → 0 score)
MAX_RECENCY_DAYS = 730.0  # 2 years


# ── Public API ─────────────────────────────────────────────────────────────────

def rank_and_trim(
    raw_context: Dict[str, Any],
    top_n: int = 10,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Rank all evidence items in the raw context and return the top-N.

    Args:
        raw_context: Aggregated retrieval dict from RetrieverService.
        top_n:       Maximum evidence items to preserve.

    Returns:
        Tuple of:
          - trimmed_context: raw_context with lists replaced by top-N items.
          - ranked_evidence: flat list of scored evidence items for the LLM.
    """
    evidence_pool: List[Dict[str, Any]] = []

    # Extract similar crimes
    if "similarity" in raw_context:
        for item in raw_context["similarity"].get("results", []):
            evidence_pool.append(_make_evidence_item(
                source="similar_crime",
                label=f"FIR {item.get('fir_number', '?')} ({item.get('crime_type', '?')})",
                data=item,
                similarity_score=item.get("similarity_score", 0.0),
                prediction_confidence=0.0,
                occurred_at=_parse_date(item.get("occurred_at")),
                severity=item.get("severity", "unknown"),
                graph_strength=0.0,
            ))

    # Extract behaviour evidence items
    if "behaviour" in raw_context:
        for fact in raw_context["behaviour"].get("evidence", []):
            evidence_pool.append(_make_evidence_item(
                source="behaviour",
                label=fact,
                data={"text": fact},
                similarity_score=0.0,
                prediction_confidence=raw_context["behaviour"].get("risk_score", 0.0),
                occurred_at=None,
                severity="high" if raw_context["behaviour"].get("risk_level") == "HIGH" else "medium",
                graph_strength=raw_context["behaviour"].get("gang_affiliation_score", 0.0),
            ))

    # Extract prediction evidence
    if "prediction" in raw_context:
        for pred_key, pred_data in raw_context["prediction"].items():
            if isinstance(pred_data, dict):
                for fact in pred_data.get("evidence", []):
                    evidence_pool.append(_make_evidence_item(
                        source=f"prediction:{pred_key}",
                        label=fact,
                        data={"text": fact, "pred_key": pred_key},
                        similarity_score=0.0,
                        prediction_confidence=pred_data.get("confidence", pred_data.get("score", 0.0) / 100.0),
                        occurred_at=None,
                        severity="high" if pred_data.get("risk_level") in ("HIGH", "CRITICAL") else "medium",
                        graph_strength=0.0,
                    ))

    # Extract geo hotspot evidence
    if "geo" in raw_context:
        for hotspot in raw_context["geo"].get("hotspots", []):
            label = (
                f"Hotspot cluster #{hotspot.get('cluster_id', '?')}: "
                f"{hotspot.get('dominant_crime_type', '?')} crimes, "
                f"risk={hotspot.get('risk_level', '?')}, "
                f"trend={hotspot.get('hotspot_trend', '?')}"
            )
            evidence_pool.append(_make_evidence_item(
                source="geo_hotspot",
                label=label,
                data=hotspot,
                similarity_score=hotspot.get("confidence_score", 0.0),
                prediction_confidence=hotspot.get("confidence_score", 0.0),
                occurred_at=None,
                severity="high" if hotspot.get("risk_level") == "High" else "medium",
                graph_strength=0.0,
            ))

    # Extract graph network evidence
    if "graph" in raw_context:
        graph_data = raw_context["graph"]
        network = graph_data.get("criminal_network", {})
        for assoc in network.get("associates", [])[:5]:
            label = (
                f"Associate: {assoc.get('name', '?')} — "
                f"strength={assoc.get('association_strength', 0):.2f}, "
                f"seen together {assoc.get('times_seen_together', 0)} times"
            )
            evidence_pool.append(_make_evidence_item(
                source="graph_network",
                label=label,
                data=assoc,
                similarity_score=0.0,
                prediction_confidence=0.0,
                occurred_at=None,
                severity="medium",
                graph_strength=float(assoc.get("association_strength", 0.0)),
            ))

    # Rank and trim
    ranked = sorted(evidence_pool, key=lambda x: x["rank_score"], reverse=True)
    top_items = ranked[:top_n]

    # Build trimmed context — replace lists in-place with top-N versions
    trimmed = _trim_context(raw_context, top_n)

    logger.debug(
        f"EvidenceRanker: pool={len(evidence_pool)}, "
        f"top_n={top_n}, kept={len(top_items)}"
    )
    return trimmed, top_items


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _make_evidence_item(
    source: str,
    label: str,
    data: Dict[str, Any],
    similarity_score: float,
    prediction_confidence: float,
    occurred_at: Optional[datetime],
    severity: str,
    graph_strength: float,
) -> Dict[str, Any]:
    """Compute a normalised rank score for a single evidence item."""
    recency = _recency_score(occurred_at)
    sev = SEVERITY_MAP.get(str(severity).lower(), 0.4)

    rank_score = (
        min(1.0, similarity_score)      * WEIGHTS["similarity_score"]
        + min(1.0, prediction_confidence) * WEIGHTS["prediction_confidence"]
        + recency                          * WEIGHTS["recency_score"]
        + sev                              * WEIGHTS["severity_score"]
        + min(1.0, graph_strength)         * WEIGHTS["graph_strength"]
    )

    return {
        "source": source,
        "label": label,
        "data": data,
        "rank_score": round(rank_score, 4),
        "similarity_score": similarity_score,
        "prediction_confidence": prediction_confidence,
        "recency_score": recency,
        "severity": severity,
        "graph_strength": graph_strength,
    }


def _recency_score(occurred_at: Optional[datetime]) -> float:
    """Converts an occurrence datetime to a [0,1] recency score."""
    if occurred_at is None:
        return 0.5  # neutral for items without timestamps

    now = datetime.now(timezone.utc)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)

    days_ago = (now - occurred_at).days
    score = max(0.0, 1.0 - (days_ago / MAX_RECENCY_DAYS))
    return round(score, 4)


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Safely parse an ISO datetime string."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _trim_context(raw_context: Dict[str, Any], top_n: int) -> Dict[str, Any]:
    """Caps list-type values inside raw_context to top_n items."""
    trimmed: Dict[str, Any] = {}
    for key, value in raw_context.items():
        if isinstance(value, dict):
            inner: Dict[str, Any] = {}
            for k, v in value.items():
                if isinstance(v, list):
                    inner[k] = v[:top_n]
                else:
                    inner[k] = v
            trimmed[key] = inner
        elif isinstance(value, list):
            trimmed[key] = value[:top_n]
        else:
            trimmed[key] = value
    return trimmed
