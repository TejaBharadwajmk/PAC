"""
PAC — AI Investigation Assistant Engine

The top-level orchestrator that coordinates the full intelligence pipeline:

    User Question
         ↓
    Intent Classifier  (deterministic rules → LLM fallback)
         ↓
    Tool Router        (selects required PAC modules)
         ↓
    Retriever Service  (calls only selected modules)
         ↓
    Evidence Ranker    (ranks and trims to top-N)
         ↓
    Context Builder    (builds structured JSON context)
         ↓
    Prompt Builder     (injects context into grounded system prompt)
         ↓
    LLM Provider       (Gemini / Ollama / Mock)
         ↓
    Response Validator (hallucination guard)
         ↓
    Final Response

Design principles:
  - Retrieval always precedes generation. The LLM never operates without context.
  - Every response includes evidence citations, confidence, and recommendations.
  - The session manager resolves entity references across follow-up questions.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tool_router import get_required_modules, get_evidence_budget
from app.services.retriever_service import RetrieverService
from app.services.evidence_ranker import rank_and_trim
from app.services.context_builder import build_context
from app.services.prompt_builder import build_prompt
from app.services.response_validator import (
    validate_response,
    extract_confidence_from_response,
    extract_recommendations,
    extract_follow_up_questions,
)
from app.services.llm_provider import BaseLLM, get_llm_provider
from app.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


# ── In-Session Conversation Memory ────────────────────────────────────────────
# Keyed by session_id. Stores last known entity references for pronoun resolution.
_sessions: Dict[str, Dict[str, Any]] = {}


class AssistantEngine:
    """Orchestrates the full AI Investigation Assistant pipeline."""

    def __init__(
        self,
        db: AsyncSession,
        neo4j_session: Optional[Any] = None,
        llm_provider: Optional[BaseLLM] = None,
    ) -> None:
        self.db = db
        self.neo4j = neo4j_session
        self.llm = llm_provider or get_llm_provider()
        self.retriever = RetrieverService(db, neo4j_session)
        self.report_gen = ReportGenerator(self.llm)

    async def chat(
        self,
        question: str,
        session_id: str = "default",
        criminal_id: Optional[str] = None,
        crime_id: Optional[str] = None,
        district: Optional[str] = None,
        gang_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process an investigator question through the full pipeline.

        Args:
            question:    Natural language investigator question.
            session_id:  Session identifier for conversation memory.
            criminal_id: Optional explicit criminal UUID.
            crime_id:    Optional explicit crime UUID.
            district:    Optional explicit district name.
            gang_name:   Optional explicit gang name.

        Returns:
            Structured assistant response dict.
        """
        t_start = time.monotonic()

        # 1. Resolve entity context from session + explicit params
        entity_context = _resolve_entity_context(
            session_id=session_id,
            question=question,
            criminal_id=criminal_id,
            crime_id=crime_id,
            district=district,
            gang_name=gang_name,
        )

        # 2. Classify intent
        intent = _classify_intent(question, entity_context)
        logger.info(f"AssistantEngine: session={session_id}, intent={intent}")

        # 3. Get required modules via Tool Router
        modules = get_required_modules(intent)
        top_n = get_evidence_budget(intent)

        # 4. Retrieve data from selected modules only
        raw_context = {}
        if modules:
            raw_context = await self.retriever.retrieve(modules, entity_context)

        # 5. Rank and trim evidence
        trimmed_context, ranked_evidence = rank_and_trim(raw_context, top_n=top_n)

        # 6. Build structured context
        context = build_context(intent, trimmed_context, ranked_evidence, entity_context)

        # 7. Build prompt
        system_prompt, user_message = build_prompt(intent, context, question)

        # 8. Generate LLM response
        try:
            raw_answer = await self.llm.generate(
                system_prompt=system_prompt,
                user_message=user_message,
                context=context,
                temperature=0.1,
            )
        except Exception as exc:
            logger.error(f"LLM generation failed: {exc}")
            raw_answer = ""

        # 9. Validate response
        validated_answer, is_valid, violations = validate_response(
            raw_answer, context, intent
        )

        # 10. Extract structured metadata
        confidence = extract_confidence_from_response(validated_answer)
        recommendations = extract_recommendations(validated_answer)
        follow_up = extract_follow_up_questions(validated_answer, intent)

        # 11. Update session memory with resolved entities
        _update_session(session_id, entity_context)

        latency_ms = round((time.monotonic() - t_start) * 1000, 1)
        logger.info(
            f"AssistantEngine: intent={intent}, valid={is_valid}, "
            f"latency={latency_ms}ms, violations={violations}"
        )

        return {
            "answer": validated_answer,
            "confidence": confidence,
            "intent": intent,
            "sources": context.get("data_sources", []),
            "evidence": context.get("evidence", [])[:8],
            "recommendations": recommendations or context.get("recommendations", [])[:3],
            "follow_up_questions": follow_up,
            "session_id": session_id,
            "is_grounded": is_valid,
            "latency_ms": latency_ms,
        }

    async def generate_investigation_summary(
        self,
        crime_id: Optional[str] = None,
        criminal_id: Optional[str] = None,
        district: Optional[str] = None,
        gang_name: Optional[str] = None,
        session_id: str = "summary",
    ) -> Dict[str, Any]:
        """Generate a full investigation briefing using all PAC modules."""
        return await self.chat(
            question="Generate a comprehensive investigation summary.",
            session_id=session_id,
            criminal_id=criminal_id,
            crime_id=crime_id,
            district=district,
            gang_name=gang_name,
        )

    async def generate_patrol_briefing(
        self,
        district: str,
        session_id: str = "patrol",
    ) -> Dict[str, Any]:
        """Generate targeted patrol recommendations for a district."""
        return await self.chat(
            question=f"Provide patrol recommendations for {district}.",
            session_id=session_id,
            district=district,
        )

    async def generate_crime_summary(
        self,
        crime_id: str,
        session_id: str = "crime",
    ) -> Dict[str, Any]:
        """Generate an analytical summary for a specific crime / FIR."""
        return await self.chat(
            question="Provide a detailed crime intelligence summary.",
            session_id=session_id,
            crime_id=crime_id,
        )

    async def generate_criminal_summary(
        self,
        criminal_id: str,
        session_id: str = "criminal",
    ) -> Dict[str, Any]:
        """Generate a full intelligence profile brief for a criminal."""
        return await self.chat(
            question="Provide a comprehensive criminal intelligence profile.",
            session_id=session_id,
            criminal_id=criminal_id,
        )

    async def generate_report(
        self,
        report_type: str,
        crime_id: Optional[str] = None,
        criminal_id: Optional[str] = None,
        district: Optional[str] = None,
        gang_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a structured intelligence report.

        Args:
            report_type: One of: fir_investigation, criminal_intelligence,
                         district_crime, hotspot_assessment, gang_intelligence.
        """
        entity_context = {
            "criminal_id": criminal_id,
            "crime_id": crime_id,
            "district": district,
            "gang_name": gang_name,
        }

        # Select relevant modules for the report type
        intent_map = {
            "fir_investigation":      "investigation_summary",
            "criminal_intelligence":  "criminal_profile",
            "district_crime":         "district_analysis",
            "hotspot_assessment":     "hotspot_analysis",
            "gang_intelligence":      "gang_analysis",
        }
        intent = intent_map.get(report_type, "investigation_summary")
        modules = get_required_modules(intent)
        top_n = get_evidence_budget(intent)

        raw_context = await self.retriever.retrieve(modules, entity_context)
        trimmed_context, ranked_evidence = rank_and_trim(raw_context, top_n=top_n)
        context = build_context(intent, trimmed_context, ranked_evidence, entity_context)

        report = await self.report_gen.generate(report_type, context)
        return report

    async def health_check(self) -> Dict[str, Any]:
        """Check LLM provider connectivity."""
        return await self.llm.health_check()


# ── Intent Classifier ──────────────────────────────────────────────────────────

# Deterministic keyword patterns (ordered by specificity — most specific first)
_INTENT_PATTERNS: List[tuple[str, List[str]]] = [
    ("investigation_summary", [
        "investigation report", "investigation summary", "full report", "full brief",
        "case summary", "briefing for fir", "investigate fir",
        "generate report", "generate summary", "generate briefing",
        "comprehensive briefing", "comprehensive summary",
    ]),
    ("similarity_search", [
        "similar crime", "similar case", "find similar", "look like",
        "same modus", "same mo", "like fir", "resemble",
        "crimes similar", "cases similar",
    ]),
    ("risk_prediction", [
        "risk level", "risk score", "risk prediction", "why is", "high risk",
        "likely to reoffend", "danger level", "reoffend", "escalation risk",
        "classified as", "classified high", "classified low",
    ]),
    ("criminal_profile", [
        "behaviour profile", "criminal profile", "explain behaviour",
        "modus operandi", "how does he operate",
    ]),
    ("criminal_network", [
        "associates", "co-offenders", "network", "connections",
        "who does he work with", "gang members linked", "his associates",
    ]),
    ("hotspot_analysis", [
        "hotspot", "hot spot", "crime cluster", "crime zone",
        "growing hotspot", "where are crimes",
    ]),
    ("district_analysis", [
        "district analysis", "crimes in district", "trend in", "crimes in",
        "region analysis", "district report", "crime trend",
        "crime analysis for", "district crime",
    ]),
    ("gang_analysis", [
        "gang", "gang threat", "active gang", "criminal gang",
        "syndicate", "cartel", "tell me about this gang",
    ]),
    ("patrol_recommendation", [
        "patrol", "deployment", "where to deploy", "police deployment",
        "beat plan", "where should police",
    ]),
    ("compare_entities", [
        "compare", "versus", "vs", "difference between",
        "which is more dangerous", "compare criminal",
    ]),
]


def _classify_intent(question: str, entity_context: Dict[str, Any]) -> str:
    """Classify the investigator's question into a supported intent.

    Uses deterministic keyword matching first.  Returns 'unknown' if
    no pattern matches (LLM-based fallback is not implemented here to
    avoid circular dependencies; the engine handles it gracefully).
    """
    q_lower = question.lower()

    for intent_name, keywords in _INTENT_PATTERNS:
        if any(kw in q_lower for kw in keywords):
            return intent_name

    # Heuristic: if entities are provided, infer intent
    if entity_context.get("crime_id") and not entity_context.get("criminal_id"):
        return "similarity_search"
    if entity_context.get("criminal_id") and not entity_context.get("crime_id"):
        return "criminal_profile"
    if entity_context.get("district") and not entity_context.get("criminal_id"):
        return "district_analysis"
    if entity_context.get("gang_name"):
        return "gang_analysis"

    return "unknown"


# ── Session Memory ─────────────────────────────────────────────────────────────

def _resolve_entity_context(
    session_id: str,
    question: str,
    criminal_id: Optional[str],
    crime_id: Optional[str],
    district: Optional[str],
    gang_name: Optional[str],
) -> Dict[str, Any]:
    """Merge explicit params with session memory for entity resolution.

    Explicit params always override session memory.  Session memory fills
    in gaps for follow-up questions like 'show his associates'.
    """
    session = _sessions.get(session_id, {})

    return {
        "criminal_id": criminal_id or session.get("criminal_id"),
        "crime_id":    crime_id    or session.get("crime_id"),
        "district":    district    or session.get("district"),
        "gang_name":   gang_name   or session.get("gang_name"),
        "query_text":  question,
    }


def _update_session(session_id: str, entity_context: Dict[str, Any]) -> None:
    """Persist resolved entities to session memory for future requests."""
    session = _sessions.get(session_id, {})
    for key in ("criminal_id", "crime_id", "district", "gang_name"):
        val = entity_context.get(key)
        if val is not None:
            session[key] = val
    _sessions[session_id] = session
