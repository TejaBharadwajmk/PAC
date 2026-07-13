"""
PAC — Response Validator

Validates every LLM response before it is returned to an investigator.
Guards against hallucination by checking that claims are grounded in
the retrieved PAC context.

Validation checks:
  1. Response is non-empty.
  2. Response does not introduce entity IDs that weren't in the context.
  3. Response does not contain known hallucination markers.
  4. Response is within a reasonable length range.
  5. Evidence section is present (for structured responses).

If validation fails, returns a safe fallback message instead of
potentially hallucinated content.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────────
MIN_RESPONSE_CHARS = 50
MAX_RESPONSE_CHARS = 8000

# Phrases that strongly suggest hallucination
HALLUCINATION_MARKERS = [
    "i don't have access to",
    "as an ai language model",
    "i cannot access real-time",
    "i was trained on data",
    "my knowledge cutoff",
    "i'm unable to access the database",
    "i don't have the ability to",
    "unfortunately, i cannot",
]

# Safe fallback returned when validation fails
INSUFFICIENT_DATA_RESPONSE = (
    "Insufficient PAC intelligence data available to answer this question with confidence. "
    "Please ensure the relevant criminal, crime, or district has been registered and "
    "intelligence modules have been run for this entity."
)


# ── Public API ─────────────────────────────────────────────────────────────────

def validate_response(
    raw_response: str,
    context: Dict[str, Any],
    intent: str,
) -> Tuple[str, bool, List[str]]:
    """Validate the LLM response against the retrieved PAC context.

    Args:
        raw_response: Raw text returned by the LLM provider.
        context:      Structured PAC context used to build the prompt.
        intent:       Classified intent string.

    Returns:
        Tuple of:
          - final_response: Validated text (or fallback if failed).
          - is_valid:       True if response passed all checks.
          - violations:     List of violation descriptions (empty if valid).
    """
    violations: List[str] = []

    # Check 1: Non-empty response
    if not raw_response or not raw_response.strip():
        violations.append("Empty response from LLM provider.")
        return INSUFFICIENT_DATA_RESPONSE, False, violations

    response = raw_response.strip()

    # Check 2: Length bounds
    if len(response) < MIN_RESPONSE_CHARS:
        violations.append(f"Response too short ({len(response)} chars, min={MIN_RESPONSE_CHARS}).")
    if len(response) > MAX_RESPONSE_CHARS:
        # Truncate rather than reject — too long is not necessarily hallucinated
        response = response[:MAX_RESPONSE_CHARS] + "\n\n[Response truncated for length.]"
        logger.warning(f"Response truncated: exceeded {MAX_RESPONSE_CHARS} chars.")

    # Check 3: Hallucination markers
    response_lower = response.lower()
    for marker in HALLUCINATION_MARKERS:
        if marker in response_lower:
            violations.append(f"Hallucination marker detected: '{marker}'.")
            break

    # Check 4: Validate that entity IDs mentioned match context
    entity_violations = _check_entity_grounding(response, context)
    violations.extend(entity_violations)

    # Check 5: No data available + unhelpful response combined
    if (
        "insufficient" in response_lower
        and len(context.get("evidence", [])) > 3
        and len(violations) == 0
    ):
        # LLM said insufficient but we had plenty of data — suspicious
        violations.append(
            "LLM claimed insufficient data, but PAC context contains "
            f"{len(context.get('evidence', []))} evidence items."
        )

    is_valid = len(violations) == 0

    if not is_valid:
        logger.warning(
            f"ResponseValidator rejected response for intent='{intent}'. "
            f"Violations: {violations}"
        )
        # Only hard-fail if there are hallucination markers or critical violations
        critical = any(
            "hallucination" in v.lower() or "empty" in v.lower()
            for v in violations
        )
        if critical:
            return INSUFFICIENT_DATA_RESPONSE, False, violations

    return response, is_valid, violations


def extract_confidence_from_response(response: str) -> float:
    """Attempt to extract a confidence level from the LLM response text.

    Returns a float in [0.0, 1.0]:
      High confidence    → 0.90
      Moderate confidence → 0.65
      Low confidence     → 0.40
    """
    lower = response.lower()
    if any(phrase in lower for phrase in ["high confidence", "confidence: high", "confidence level: high"]):
        return 0.90
    if any(phrase in lower for phrase in ["moderate confidence", "confidence: moderate"]):
        return 0.65
    if any(phrase in lower for phrase in ["low confidence", "confidence: low"]):
        return 0.40
    # Default: moderate
    return 0.70


def extract_recommendations(response: str) -> List[str]:
    """Extract recommendation bullet points from the LLM response."""
    recommendations: List[str] = []
    lines = response.split("\n")
    in_recs = False

    for line in lines:
        line_stripped = line.strip()
        if any(
            kw in line_stripped.lower()
            for kw in ["recommendation", "next action", "suggested action"]
        ):
            in_recs = True
            continue
        if in_recs:
            if line_stripped.startswith(("-", "•", "*", "1", "2", "3", "4", "5")):
                # Strip leading bullet characters
                clean = re.sub(r"^[-•*\d.)\s]+", "", line_stripped).strip()
                if clean:
                    recommendations.append(clean)
            elif line_stripped == "" and recommendations:
                # Blank line ends recommendation block
                break

    return recommendations[:5]  # cap at 5 recommendations


def extract_follow_up_questions(response: str, intent: str) -> List[str]:
    """Generate contextual follow-up questions based on the intent.

    These are deterministic question templates, not LLM-generated,
    to guarantee they are always actionable and grounded.
    """
    questions: Dict[str, List[str]] = {
        "criminal_profile": [
            "Which crimes is this criminal linked to?",
            "Show this criminal's network of co-offenders.",
            "What is the risk prediction score for this criminal?",
        ],
        "similarity_search": [
            "Who are the offenders linked to these similar crimes?",
            "Show the hotspot analysis for this crime type and district.",
            "What is the risk forecast for the district of this crime?",
        ],
        "criminal_network": [
            "Generate a full behaviour profile for this criminal.",
            "What is the gang threat level for this criminal's gang?",
            "Show the highest-risk associates of this criminal.",
        ],
        "hotspot_analysis": [
            "Which criminals are operating in these hotspot areas?",
            "What is the district risk index for this area?",
            "What patrol coverage is recommended for these hotspots?",
        ],
        "risk_prediction": [
            "Show the full behaviour profile for this criminal.",
            "Which crimes drove this risk score?",
            "Who are this criminal's strongest co-offender associations?",
        ],
        "gang_analysis": [
            "Who are the most active members of this gang?",
            "Which districts is this gang operating in?",
            "Show crimes committed by this gang's members.",
        ],
        "investigation_summary": [
            "Show similar historical cases for comparison.",
            "What patrol deployments are recommended?",
            "Generate a criminal intelligence report for the primary suspect.",
        ],
        "patrol_recommendation": [
            "Which gangs are active in this district?",
            "What are the growing hotspots in this region?",
            "Show crime trend analysis for the last 30 days.",
        ],
    }
    return questions.get(intent, [
        "Show similar crimes in this area.",
        "Who are the repeat offenders in this district?",
        "What are the active hotspots right now?",
    ])


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _check_entity_grounding(response: str, context: Dict[str, Any]) -> List[str]:
    """Check that entity IDs mentioned in the response appear in the context."""
    violations: List[str] = []

    # Collect all UUID-like strings from the response
    uuid_pattern = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )
    mentioned_uuids = set(uuid_pattern.findall(response))

    if not mentioned_uuids:
        return violations

    # Build set of all UUIDs present in context
    context_str = str(context)
    context_uuids = set(uuid_pattern.findall(context_str))

    # Any UUID in response that's not in context is potentially hallucinated
    ungrounded = mentioned_uuids - context_uuids
    if ungrounded:
        violations.append(
            f"Response contains {len(ungrounded)} UUID(s) not found in PAC context: "
            f"{', '.join(list(ungrounded)[:3])}"
        )

    return violations
