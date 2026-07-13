"""
PAC — Behavior Router

Exposes behaviour intelligence endpoints.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException, BackgroundTasks
from neo4j import AsyncSession

from app.dependencies import DbSession, CurrentUser
from app.graph_db import get_neo4j_session
from app.services.behavior_service import BehaviorService
from app.schemas.behavior import (
    BehaviourProfileResponse,
    HighRiskCriminalsResponse,
    BehaviorStatisticsResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter()


@router.get(
    "/criminal/{criminal_id}",
    response_model=BehaviourProfileResponse,
    summary="Get behavior profile",
    description="Calculates or retrieves the behaviour intelligence profile for a criminal.",
)
async def get_criminal_behavior_profile(
    criminal_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = BehaviorService(db, graph_db)
    profile = await service.get_or_generate_profile(criminal_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criminal profile not found: {criminal_id}",
        )
    return profile.detailed_metrics


@router.get(
    "/high-risk",
    response_model=List[HighRiskCriminalsResponse],
    summary="Get high risk criminals",
    description="Retrieves a list of criminals sorted by calculated risk score.",
)
async def get_high_risk_criminals(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    service = BehaviorService(db)
    profiles = await service.repo.get_high_risk(limit=limit, offset=offset)
    
    results = []
    for p in profiles:
        results.append(HighRiskCriminalsResponse(
            criminal_id=p.criminal_id,
            name=p.criminal.name if p.criminal else "Unknown",
            aliases=p.criminal.aliases if p.criminal and p.criminal.aliases else [],
            risk_score=p.risk_score,
            risk_level=p.risk_level,
            primary_crime_type=p.preferred_modus_operandi[0] if p.preferred_modus_operandi else "Unknown",
            last_generated_at=p.last_updated or p.generated_at
        ))
    return results


@router.get(
    "/repeat-offenders",
    response_model=List[HighRiskCriminalsResponse],
    summary="Get repeat offenders",
    description="Retrieves criminals sorted by repeat offender score.",
)
async def get_repeat_offenders(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    service = BehaviorService(db)
    profiles = await service.repo.get_repeat_offenders(limit=limit, offset=offset)
    
    results = []
    for p in profiles:
        results.append(HighRiskCriminalsResponse(
            criminal_id=p.criminal_id,
            name=p.criminal.name if p.criminal else "Unknown",
            aliases=p.criminal.aliases if p.criminal and p.criminal.aliases else [],
            risk_score=p.risk_score,
            risk_level=p.risk_level,
            primary_crime_type=p.preferred_modus_operandi[0] if p.preferred_modus_operandi else "Unknown",
            last_generated_at=p.last_updated or p.generated_at
        ))
    return results


@router.get(
    "/serial-patterns",
    response_model=List[BehaviourProfileResponse],
    summary="Identify serial patterns",
    description="Filters profiles meeting a behaviour consistency threshold.",
)
async def get_serial_patterns(
    db: DbSession,
    current_user: CurrentUser,
    min_consistency: float = Query(0.6, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    service = BehaviorService(db)
    profiles = await service.repo.get_serial_patterns(
        min_consistency=min_consistency,
        limit=limit,
        offset=offset
    )
    return [p.detailed_metrics for p in profiles]


@router.get(
    "/statistics",
    response_model=BehaviorStatisticsResponse,
    summary="Behavior overview statistics",
)
async def get_behavior_statistics(
    db: DbSession,
    current_user: CurrentUser,
):
    service = BehaviorService(db)
    return await service.repo.get_statistics()


@router.post(
    "/rebuild",
    response_model=MessageResponse,
    summary="Rebuild all behavior profiles",
    description="Wipes and regenerates all behavior profiles in the background.",
)
async def rebuild_behavior_profiles(
    db: DbSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = BehaviorService(db, graph_db)
    background_tasks.add_task(service.rebuild_all_profiles)
    return MessageResponse(
        message="Background rebuild of behavior profiles initiated successfully."
    )
