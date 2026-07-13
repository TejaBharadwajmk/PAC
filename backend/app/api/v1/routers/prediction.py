"""
PAC — Predictions Router

Exposes REST API endpoints for predictive intelligence risk scores,
threat levels, district index ratings, and investigation priority queues.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from neo4j import AsyncSession as Neo4jSession

from app.database import get_db_session
from app.graph_db import get_neo4j_session
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.prediction import PredictionResponse, PredictionStatisticsResponse
from app.services.prediction_service import PredictionService

router = APIRouter(tags=["Predictive Intelligence"])


@router.get(
    "/criminal/{criminal_id}",
    response_model=PredictionResponse,
    summary="Get Criminal Risk Forecast"
)
async def get_criminal_prediction(
    criminal_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    g_session: Neo4jSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieves or computes the risk forecast profile for a criminal."""
    service = PredictionService(db, g_session)
    pred = await service.get_or_generate_criminal_prediction(criminal_id)
    if not pred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Criminal not found or predictive calculations failed."
        )
    return pred


@router.get(
    "/district/{district}",
    response_model=PredictionResponse,
    summary="Get District Risk Index"
)
async def get_district_prediction(
    district: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieves or calculates the District Risk Index score."""
    service = PredictionService(db)
    pred = await service.repo.get_by_entity("district", district)
    if not pred:
        pred = await service.generate_district_prediction(district)
    return pred


@router.get(
    "/hotspots",
    response_model=List[PredictionResponse],
    summary="Get Hotspot Growth Forecasts"
)
async def get_hotspot_predictions(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieves growth forecast snapshots for active hotspot regions."""
    service = PredictionService(db)
    # Check if hotspot forecasts exist, otherwise calculate
    preds = await service.repo.get_highest_risk_criminals() # using get_highest_risk_criminals wrapper
    # Let's filter hotspot forecasts from db
    from sqlalchemy import select
    from app.models.prediction import PredictionProfile
    stmt = select(PredictionProfile).where(PredictionProfile.entity_type == "hotspot")
    res = await db.execute(stmt)
    list_preds = list(res.scalars().all())
    if not list_preds:
        list_preds = await service.generate_hotspot_predictions()
    return list_preds


@router.get(
    "/gangs",
    response_model=List[PredictionResponse],
    summary="Get Gang Threat Rankings"
)
async def get_gang_predictions(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieves gang threat rankings and threat score breakdowns."""
    service = PredictionService(db)
    return await service.repo.get_gang_rankings()


@router.get(
    "/investigations",
    response_model=List[PredictionResponse],
    summary="Get Investigation Priority Queue"
)
async def get_investigation_priority_queue(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieves the prioritized queue of active investigations."""
    service = PredictionService(db)
    return await service.repo.get_investigation_queue()


@router.get(
    "/statistics",
    response_model=PredictionStatisticsResponse,
    summary="Get Prediction Performance Statistics"
)
async def get_prediction_statistics(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Gathers distribution analytics across criminal risk prediction snapshots."""
    service = PredictionService(db)
    return await service.repo.get_statistics()


@router.post(
    "/rebuild",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Rebuild All Predictions"
)
async def rebuild_all_predictions(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    g_session: Neo4jSession = Depends(get_neo4j_session),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an asynchronous rebuild of all predictive models.
    Available to all authenticated personnel.
    """
    async def run_rebuild():
        async with db.begin():
            service = PredictionService(db, g_session)
            await service.rebuild_all_predictions()

    background_tasks.add_task(run_rebuild)
    return {"message": "Asynchronous rebuild of all predictions started in background."}
