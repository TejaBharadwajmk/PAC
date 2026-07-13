"""
PAC — Criminals Router

Endpoints:
  POST  /api/v1/criminals/                    — Register criminal profile
  GET   /api/v1/criminals/                    — List criminals (filters)
  GET   /api/v1/criminals/{id}                — Get criminal by ID
  PUT   /api/v1/criminals/{id}                — Update criminal profile
  GET   /api/v1/criminals/{id}/crimes         — All crimes for a criminal
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, status, Query, BackgroundTasks

from app.dependencies import DbSession, CurrentUser
from app.schemas.criminal import (
    CriminalCreate, CriminalUpdate, CriminalResponse, CriminalListItem,
)
from app.schemas.common import MessageResponse
from app.models.criminal import Criminal
from app.repositories.criminal_repo import CriminalRepository
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.post(
    "/",
    response_model=CriminalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register criminal profile",
)
async def register_criminal(
    data: CriminalCreate,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
):
    """Register a new accused/suspect profile in the system."""
    repo = CriminalRepository(db)
    criminal = Criminal(
        name=data.name,
        aliases=data.aliases,
        date_of_birth=data.date_of_birth,
        age=data.age,
        gender=data.gender,
        district=data.district,
        state=data.state,
        address=data.address,
        contact_number=data.contact_number,
        gang_name=data.gang_name,
        gang_affiliation=data.gang_affiliation,
        height_cm=data.height_cm,
        build=data.build,
        identifying_marks=data.identifying_marks,
        is_wanted=data.is_wanted,
    )
    new_criminal = await repo.create(criminal)
    from app.services.graph_service import sync_criminal_to_graph
    background_tasks.add_task(sync_criminal_to_graph, new_criminal.id)
    return new_criminal


@router.get(
    "/",
    response_model=List[CriminalListItem],
    summary="List criminals",
)
async def list_criminals(
    district: Optional[str] = Query(None),
    is_wanted: Optional[bool] = Query(None),
    is_repeat_offender: Optional[bool] = Query(None),
    name_search: Optional[str] = Query(None, description="Partial name search"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: DbSession = ...,
    current_user: CurrentUser = ...,
):
    repo = CriminalRepository(db)

    if name_search:
        return await repo.search_by_name(name_search, limit=limit)
    if is_wanted:
        return await repo.get_wanted(limit=limit)
    if is_repeat_offender:
        return await repo.get_repeat_offenders(district=district, limit=limit)

    filters = {}
    if district:
        filters["district"] = district

    return await repo.get_all(skip=skip, limit=limit, filters=filters)


@router.get(
    "/{criminal_id}",
    response_model=CriminalResponse,
    summary="Get criminal profile",
)
async def get_criminal(
    criminal_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    repo = CriminalRepository(db)
    criminal = await repo.get_with_details(criminal_id)
    if not criminal:
        raise NotFoundError("Criminal", str(criminal_id))
    return criminal


@router.put(
    "/{criminal_id}",
    response_model=CriminalResponse,
    summary="Update criminal profile",
)
async def update_criminal(
    criminal_id: UUID,
    data: CriminalUpdate,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
):
    repo = CriminalRepository(db)
    criminal = await repo.get(criminal_id)
    if not criminal:
        raise NotFoundError("Criminal", str(criminal_id))

    for field, value in data.model_dump(exclude_unset=True).items():
        if hasattr(criminal, field):
            setattr(criminal, field, value)

    updated_criminal = await repo.save(criminal)
    from app.services.graph_service import sync_criminal_to_graph
    background_tasks.add_task(sync_criminal_to_graph, criminal_id)
    return updated_criminal


@router.get(
    "/{criminal_id}/crimes",
    summary="Get all crimes for a criminal",
)
async def get_criminal_crimes(
    criminal_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Return all crime associations for a criminal with crime summary data."""
    repo = CriminalRepository(db)
    if not await repo.exists(criminal_id):
        raise NotFoundError("Criminal", str(criminal_id))

    links = await repo.get_crimes_for_criminal(criminal_id)
    return [
        {
            "crime_id": str(lnk.crime_id),
            "role": lnk.role.value,
            "is_arrested": lnk.is_arrested,
            "arrest_date": lnk.arrest_date.isoformat() if lnk.arrest_date else None,
            "notes": lnk.notes,
            "crime": {
                "fir_number": lnk.crime.fir_number,
                "crime_type": lnk.crime.crime_type.value,
                "district": lnk.crime.district,
                "severity": lnk.crime.severity.value,
                "status": lnk.crime.status.value,
                "occurred_at": lnk.crime.occurred_at.isoformat(),
            } if lnk.crime else None,
        }
        for lnk in links
    ]
