"""
PAC — AI Investigation Assistant Router

Exposes the AI Investigation Assistant pipeline as REST API endpoints.
All responses follow the uniform AssistantChatResponse schema.

Endpoints:
  POST /chat                  — General investigation query
  POST /investigation-summary — Full investigation briefing
  POST /patrol-briefing       — District patrol recommendations
  POST /crime-summary         — Crime / FIR analytical summary
  POST /criminal-summary      — Criminal intelligence profile brief
  POST /report                — Generate structured intelligence report
  GET  /health                — LLM provider health check
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncSession

from app.dependencies import DbSession, CurrentUser
from app.graph_db import get_neo4j_session
from app.services.assistant_engine import AssistantEngine
from app.services.tool_router import all_supported_intents
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    InvestigationSummaryRequest,
    PatrolBriefingRequest,
    CrimeSummaryRequest,
    CriminalSummaryRequest,
    ReportRequest,
    ReportResponse,
    AssistantHealthResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Shared Engine Factory ──────────────────────────────────────────────────────

def _get_engine(db: DbSession, graph_db: AsyncSession) -> AssistantEngine:
    """Instantiate the AssistantEngine with both database sessions."""
    return AssistantEngine(db=db, neo4j_session=graph_db)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="AI Investigation Chat",
    description=(
        "Send an investigation question to the PAC AI Assistant. "
        "The assistant classifies intent, retrieves only the required PAC intelligence "
        "modules, ranks evidence, and generates a grounded, evidence-backed response. "
        "Supports multi-turn conversations via session_id."
    ),
    status_code=status.HTTP_200_OK,
)
async def chat(
    request: AssistantChatRequest,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    """General investigation question with conversation memory."""
    engine = _get_engine(db, graph_db)
    try:
        result = await engine.chat(
            question=request.question,
            session_id=request.session_id,
            criminal_id=request.criminal_id,
            crime_id=request.crime_id,
            district=request.district,
            gang_name=request.gang_name,
        )
    except Exception as exc:
        logger.error(f"AssistantEngine.chat failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Assistant pipeline error: {str(exc)}",
        )
    return AssistantChatResponse(**result)


@router.post(
    "/investigation-summary",
    response_model=AssistantChatResponse,
    summary="Generate Investigation Summary",
    description=(
        "Generate a comprehensive investigation briefing by running all PAC "
        "intelligence modules (DNA, Similarity, Behaviour, Prediction, Graph, Geo)."
    ),
    status_code=status.HTTP_200_OK,
)
async def investigation_summary(
    request: InvestigationSummaryRequest,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    """Full investigation brief using all PAC modules."""
    engine = _get_engine(db, graph_db)
    try:
        result = await engine.generate_investigation_summary(
            crime_id=request.crime_id,
            criminal_id=request.criminal_id,
            district=request.district,
            gang_name=request.gang_name,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error(f"Investigation summary failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    return AssistantChatResponse(**result)


@router.post(
    "/patrol-briefing",
    response_model=AssistantChatResponse,
    summary="District Patrol Briefing",
    description=(
        "Generate targeted patrol recommendations for a district by combining "
        "Geo Intelligence hotspot data and Predictive Intelligence district risk scores."
    ),
    status_code=status.HTTP_200_OK,
)
async def patrol_briefing(
    request: PatrolBriefingRequest,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    """Patrol recommendations for a specific district."""
    engine = _get_engine(db, graph_db)
    try:
        result = await engine.generate_patrol_briefing(
            district=request.district,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error(f"Patrol briefing failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    return AssistantChatResponse(**result)


@router.post(
    "/crime-summary",
    response_model=AssistantChatResponse,
    summary="Crime / FIR Analytical Summary",
    description=(
        "Generate an analytical intelligence summary for a specific crime / FIR. "
        "Retrieves Crime DNA, similar cases, and geo intelligence."
    ),
    status_code=status.HTTP_200_OK,
)
async def crime_summary(
    request: CrimeSummaryRequest,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    """Analytical summary for a specific crime."""
    engine = _get_engine(db, graph_db)
    try:
        result = await engine.generate_crime_summary(
            crime_id=request.crime_id,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error(f"Crime summary failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    return AssistantChatResponse(**result)


@router.post(
    "/criminal-summary",
    response_model=AssistantChatResponse,
    summary="Criminal Intelligence Profile Brief",
    description=(
        "Generate a full intelligence profile brief for a specific criminal. "
        "Retrieves Behaviour Profile, Prediction, and Neo4j network data."
    ),
    status_code=status.HTTP_200_OK,
)
async def criminal_summary(
    request: CriminalSummaryRequest,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    """Full intelligence brief for a criminal."""
    engine = _get_engine(db, graph_db)
    try:
        result = await engine.generate_criminal_summary(
            criminal_id=request.criminal_id,
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.error(f"Criminal summary failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    return AssistantChatResponse(**result)


@router.post(
    "/report",
    response_model=ReportResponse,
    summary="Generate Intelligence Report",
    description=(
        "Generate a structured police intelligence report. "
        "Supported types: fir_investigation, criminal_intelligence, "
        "district_crime, hotspot_assessment, gang_intelligence."
    ),
    status_code=status.HTTP_200_OK,
)
async def generate_report(
    request: ReportRequest,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    """Generate a structured intelligence report."""
    engine = _get_engine(db, graph_db)
    try:
        report = await engine.generate_report(
            report_type=request.report_type,
            crime_id=request.crime_id,
            criminal_id=request.criminal_id,
            district=request.district,
            gang_name=request.gang_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    return ReportResponse(**report)


@router.get(
    "/health",
    response_model=AssistantHealthResponse,
    summary="AI Assistant Health Check",
    description="Check LLM provider connectivity and list supported intents.",
    status_code=status.HTTP_200_OK,
)
async def assistant_health(
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    """LLM provider health check and module availability."""
    engine = _get_engine(db, graph_db)
    llm_health = await engine.health_check()

    return AssistantHealthResponse(
        provider=llm_health.get("provider", "unknown"),
        model=llm_health.get("model"),
        status=llm_health.get("status", "unknown"),
        available_modules=[
            "Crime DNA",
            "Hybrid Similarity Engine",
            "Behaviour Intelligence",
            "Predictive Intelligence",
            "Criminal Network Intelligence (Neo4j)",
            "Geo Intelligence",
        ],
        supported_intents=all_supported_intents(),
    )
