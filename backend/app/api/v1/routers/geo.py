"""
PAC — Geo Intelligence Router
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status

from app.dependencies import DbSession, CurrentUser
from app.schemas.geo import HotspotResponse, GeoStatisticsResponse
from app.services.geo_service import GeoService
from app.models.crime import CrimeType

router = APIRouter()


@router.get(
    "/hotspots",
    response_model=List[HotspotResponse],
    summary="Get spatial hotspots",
    description="Identifies spatial crime clusters using PostGIS DBSCAN clustering.",
)
async def get_hotspots(
    db: DbSession,
    current_user: CurrentUser,
    eps: float = Query(1000.0, ge=10.0, le=50000.0, description="DBSCAN search radius in meters"),
    min_samples: int = Query(5, ge=2, le=500, description="DBSCAN minimum samples for a cluster"),
    district: Optional[str] = Query(None, description="Optional district filter"),
    crime_type: Optional[CrimeType] = Query(None, description="Optional crime type filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
):
    service = GeoService(db)
    crime_type_str = crime_type.value if crime_type else None
    return await service.get_hotspots(
        eps=eps,
        min_samples=min_samples,
        district=district,
        crime_type=crime_type_str,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/district/{district}",
    response_model=List[HotspotResponse],
    summary="Get hotspots filtered by district",
    description="Identifies crime hotspots within a specific police district.",
)
async def get_district_hotspots(
    district: str,
    db: DbSession,
    current_user: CurrentUser,
    eps: float = Query(1000.0, ge=10.0, le=50000.0, description="DBSCAN search radius in meters"),
    min_samples: int = Query(5, ge=2, le=500, description="DBSCAN minimum samples for a cluster"),
    crime_type: Optional[CrimeType] = Query(None, description="Optional crime type filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
):
    service = GeoService(db)
    crime_type_str = crime_type.value if crime_type else None
    return await service.get_hotspots(
        eps=eps,
        min_samples=min_samples,
        district=district,
        crime_type=crime_type_str,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/crime-type/{crime_type}",
    response_model=List[HotspotResponse],
    summary="Get hotspots filtered by crime type",
    description="Identifies hotspots for a particular category of crime.",
)
async def get_crime_type_hotspots(
    crime_type: CrimeType,
    db: DbSession,
    current_user: CurrentUser,
    eps: float = Query(1000.0, ge=10.0, le=50000.0, description="DBSCAN search radius in meters"),
    min_samples: int = Query(5, ge=2, le=500, description="DBSCAN minimum samples for a cluster"),
    district: Optional[str] = Query(None, description="Optional district filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
):
    service = GeoService(db)
    return await service.get_hotspots(
        eps=eps,
        min_samples=min_samples,
        district=district,
        crime_type=crime_type.value,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/statistics",
    response_model=GeoStatisticsResponse,
    summary="Get spatial statistics summary",
    description="Returns aggregate statistical metadata for hotspots and crime density.",
)
async def get_statistics(
    db: DbSession,
    current_user: CurrentUser,
    eps: float = Query(1000.0, ge=10.0, le=50000.0, description="DBSCAN search radius in meters"),
    min_samples: int = Query(5, ge=2, le=500, description="DBSCAN minimum samples for a cluster"),
    district: Optional[str] = Query(None, description="Optional district filter"),
    crime_type: Optional[CrimeType] = Query(None, description="Optional crime type filter"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
):
    service = GeoService(db)
    crime_type_str = crime_type.value if crime_type else None
    return await service.get_statistics(
        eps=eps,
        min_samples=min_samples,
        district=district,
        crime_type=crime_type_str,
        start_date=start_date,
        end_date=end_date,
    )
