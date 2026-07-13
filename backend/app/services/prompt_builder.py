"""
PAC — Prompt Builder

Constructs grounded, investigator-focused system and user prompts
for each intent type.  Every prompt:

  1. Instructs the model to NEVER invent facts not present in context.
  2. Provides the structured PAC context as the only allowable data source.
  3. Asks for reasoning, evidence citations, and confidence level.
  4. Instructs the model to flag uncertainty when data is incomplete.
  5. Formats output for investigative readability, not casual conversation.
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Master Grounding System Prompt ────────────────────────────────────────────
_SYSTEM_BASE = """You are the PAC AI Investigation Assistant for Karnataka State Police.
Your role is to help investigators solve crimes using ONLY the PAC intelligence data provided.

MANDATORY RULES:
1. NEVER invent, assume, or hallucinate facts not explicitly present in the provided PAC context.
2. ONLY use information from the PAC context below. Do not use any general knowledge to fill gaps.
3. ALWAYS cite specific evidence from the evidence list when making a claim.
4. If the data is insufficient, say so explicitly: "Insufficient PAC data available."
5. Use concise, professional language suitable for law enforcement investigators.
6. Always provide a confidence level (High / Moderate / Low) based on available evidence quality.
7. Format your response with clear sections: Findings, Evidence, Recommendations, Follow-up Questions.

PAC CONTEXT:
{context_json}

---
Respond only to the investigator's question below using the above context."""

# ── Intent-Specific Prompt Additions ──────────────────────────────────────────
_INTENT_INSTRUCTIONS: Dict[str, str] = {
    "similarity_search": (
        "Focus on the similar crime matches. Explain what MO patterns connect them. "
        "Highlight the top 3 most similar cases with reasons."
    ),
    "criminal_profile": (
        "Analyse this criminal's complete behaviour profile. "
        "Explain their risk level, MO patterns, escalation trend, and gang affiliation. "
        "Provide concrete operational recommendations."
    ),
    "criminal_network": (
        "Describe the criminal's network of co-offenders from the graph data. "
        "Identify the strongest associations and any gang connections. "
        "Flag high-risk network clusters."
    ),
    "hotspot_analysis": (
        "Analyse the active crime hotspots. Identify the highest-risk clusters, "
        "dominant crime types, peak times, and trend direction. "
        "Recommend specific patrol windows for each hotspot."
    ),
    "district_analysis": (
        "Provide a crime intelligence assessment for this district. "
        "Cover risk level, dominant crime types, hotspot count, and gang activity. "
        "Recommend resource allocation and patrol strategy."
    ),
    "gang_analysis": (
        "Analyse the gang's threat level, membership, and crime history. "
        "Identify key members, co-offending patterns, and operational territory. "
        "Recommend targeted interventions."
    ),
    "risk_prediction": (
        "Explain WHY this criminal is at the stated risk level. "
        "Break down the contributing score factors. "
        "Cite specific behaviour evidence that drives the risk score. "
        "Recommend preventive investigation actions."
    ),
    "investigation_summary": (
        "Generate a comprehensive investigation briefing. Cover: "
        "crime details, linked similar cases, offender profiles, "
        "network connections, geo analysis, and risk forecast. "
        "End with prioritised next actions for the investigating officer."
    ),
    "patrol_recommendation": (
        "Provide specific, actionable patrol recommendations for this district. "
        "Include hotspot locations, peak crime windows, priority areas, "
        "and resource requirements. Be operationally specific."
    ),
    "compare_entities": (
        "Compare the two criminal profiles side by side. "
        "Cover: risk levels, primary crime types, MO patterns, network strength, "
        "and prediction scores. Summarise which presents the higher threat."
    ),
    "unknown": (
        "Answer the investigator's question using only the available PAC data. "
        "If the data is insufficient, explain what is missing."
    ),
}


def build_prompt(
    intent: str,
    context: Dict[str, Any],
    user_question: str,
) -> tuple[str, str]:
    """Build the system prompt and user message for the LLM.

    Args:
        intent:        Classified intent string.
        context:       Structured context from ContextBuilder.
        user_question: The investigator's original question.

    Returns:
        Tuple of (system_prompt, user_message).
    """
    # Serialise context to compact JSON — exclude very large fields
    context_for_prompt = _prepare_context_for_prompt(context)
    context_json = json.dumps(context_for_prompt, indent=2, default=str)

    # Build system prompt
    intent_instruction = _INTENT_INSTRUCTIONS.get(intent, _INTENT_INSTRUCTIONS["unknown"])
    system_prompt = _SYSTEM_BASE.format(context_json=context_json)
    system_prompt += f"\n\nINSTRUCTION: {intent_instruction}"

    # Build user message with data source attribution
    sources = context.get("data_sources", [])
    sources_str = ", ".join(sources) if sources else "No PAC modules retrieved"

    user_message = (
        f"Investigator Question: {user_question}\n\n"
        f"Available PAC Intelligence Sources: {sources_str}\n"
        f"Evidence Items Available: {len(context.get('evidence', []))}\n\n"
        f"Provide your analysis:"
    )

    logger.debug(
        f"PromptBuilder: intent={intent}, "
        f"context_chars={len(context_json)}, "
        f"sources={sources}"
    )
    return system_prompt, user_message


def build_report_prompt(
    report_type: str,
    context: Dict[str, Any],
) -> tuple[str, str]:
    """Build a structured report generation prompt.

    Args:
        report_type: One of the 5 supported report types.
        context:     Structured PAC context.

    Returns:
        Tuple of (system_prompt, user_message).
    """
    context_for_prompt = _prepare_context_for_prompt(context)
    context_json = json.dumps(context_for_prompt, indent=2, default=str)

    system_prompt = _SYSTEM_BASE.format(context_json=context_json)
    system_prompt += (
        "\n\nINSTRUCTION: Generate a formal police intelligence report. "
        "Structure it with these exact sections:\n"
        "1. EXECUTIVE SUMMARY (2-3 sentences)\n"
        "2. KEY FINDINGS (bullet points, facts only)\n"
        "3. EVIDENCE (cite specific PAC data points)\n"
        "4. RISK ASSESSMENT (from prediction data)\n"
        "5. RECOMMENDATIONS (operational directives)\n"
        "6. SUGGESTED NEXT ACTIONS (numbered, prioritised)\n\n"
        "Use formal law enforcement report language. Every claim must cite PAC data."
    )

    user_message = f"Generate a {report_type} using the provided PAC intelligence context."
    return system_prompt, user_message


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _prepare_context_for_prompt(context: Dict[str, Any]) -> Dict[str, Any]:
    """Remove verbose or redundant fields before JSON serialisation."""
    prepared = {}

    for key, value in context.items():
        # Skip empty dicts/lists
        if isinstance(value, dict) and not value:
            continue
        if isinstance(value, list) and not value:
            continue

        # Cap mo_summary length
        if key == "crime_summary" and isinstance(value, dict):
            v = dict(value)
            if "mo_summary" in v and v["mo_summary"]:
                v["mo_summary"] = v["mo_summary"][:200]
            prepared[key] = v
        else:
            prepared[key] = value

    return prepared
