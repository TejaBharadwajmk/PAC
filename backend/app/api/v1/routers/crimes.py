"""
PAC — Crime Registration Router

Endpoints:
  POST   /api/v1/crimes/           — Register new crime (FIR)
  GET    /api/v1/crimes/           — List crimes (paginated + filtered)
  GET    /api/v1/crimes/{id}       — Get crime by UUID
  GET    /api/v1/crimes/fir/{no}   — Get crime by FIR number
  PUT    /api/v1/crimes/{id}       — Update crime
  DELETE /api/v1/crimes/{id}       — Delete crime (admin only)
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, status, Query, Depends

from app.dependencies import DbSession, CurrentUser, require_roles
from app.schemas.crime import (
    CrimeCreate, CrimeUpdate, CrimeResponse,
    CrimeListItem, CrimeFilterParams,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.crime_service import CrimeService
from app.models.crime import CrimeType, CrimeStatus, CrimeSeverity
from app.models.user import UserRole

router = APIRouter()


@router.post(
    "/",
    response_model=CrimeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new crime (FIR)",
    description=(
        "Register a new FIR. If mo_text is provided, MO features are automatically "
        "extracted using the rule-based MO Intelligence Engine. "
        "Crime DNA (vector embedding) is generated asynchronously by the ML Engine."
    ),
)
async def register_crime(
    data: CrimeCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    service = CrimeService(db)
    return await service.register_crime(data, current_user)


@router.get(
    "/",
    response_model=PaginatedResponse[CrimeListItem],
    summary="List crimes",
    description="Paginated list of crimes with optional filters by district, type, status, severity, and date range.",
)
async def list_crimes(
    district: Optional[str] = Query(None, description="Filter by district name"),
    crime_type: Optional[CrimeType] = Query(None),
    status_filter: Optional[CrimeStatus] = Query(None, alias="status"),
    severity: Optional[CrimeSeverity] = Query(None),
    from_date: Optional[datetime] = Query(None, description="ISO 8601 datetime"),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: DbSession = ...,
    current_user: CurrentUser = ...,
):
    params = CrimeFilterParams(
        district=district,
        crime_type=crime_type,
        status=status_filter,
        severity=severity,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    service = CrimeService(db)
    crimes, total = await service.list_crimes(params)

    return PaginatedResponse(
        items=[CrimeListItem.model_validate(c) for c in crimes],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
        has_prev=page > 1,
    )


@router.get(
    "/fir/{fir_number}",
    response_model=CrimeResponse,
    summary="Get crime by FIR number",
)
async def get_crime_by_fir(
    fir_number: str,
    db: DbSession,
    current_user: CurrentUser,
):
    service = CrimeService(db)
    return await service.get_crime_by_fir(fir_number)


@router.get(
    "/{crime_id}",
    response_model=CrimeResponse,
    summary="Get crime by ID",
)
async def get_crime(
    crime_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    service = CrimeService(db)
    return await service.get_crime(crime_id)


@router.put(
    "/{crime_id}",
    response_model=CrimeResponse,
    summary="Update crime record",
)
async def update_crime(
    crime_id: UUID,
    data: CrimeUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    service = CrimeService(db)
    return await service.update_crime(crime_id, data, current_user)


@router.delete(
    "/{crime_id}",
    response_model=MessageResponse,
    summary="Delete crime record (admin only)",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def delete_crime(
    crime_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    service = CrimeService(db)
    await service.delete_crime(crime_id)
    return MessageResponse(message=f"Crime {crime_id} deleted successfully")
