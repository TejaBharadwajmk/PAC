"""
PAC — Crime Schemas (Pydantic v2)

Request bodies, response models, and filter params for the Crime Registration module.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.crime import CrimeType, CrimeStatus, CrimeSeverity


# ── MO Feature Schemas ─────────────────────────────────────

class CrimeMOCreate(BaseModel):
    """Structured MO features — provided by client or auto-extracted."""
    crime_method: Optional[str] = None
    entry_method: Optional[str] = None
    target_type: Optional[str] = None
    weapon_used: Optional[str] = "none"
    tools_used: List[str] = Field(default_factory=list)
    time_of_day: Optional[str] = None
    day_type: Optional[str] = None
    planning_level: Optional[str] = "opportunistic"
    gang_involved: bool = False
    num_accused: int = Field(default=1, ge=1, le=100)
    escape_method: Optional[str] = "unknown"
    vehicle_used_in_crime: bool = False
    modus_operandi_tags: List[str] = Field(default_factory=list)


class CrimeMOResponse(CrimeMOCreate):
    id: UUID
    crime_id: UUID
    extraction_method: str
    extracted_at: datetime

    model_config = {"from_attributes": True}


# ── Crime CRUD Schemas ─────────────────────────────────────

class CrimeCreate(BaseModel):
    fir_number: str = Field(..., min_length=1, max_length=100, description="Unique FIR number")
    crime_type: CrimeType
    severity: CrimeSeverity = CrimeSeverity.MEDIUM

    # Location
    district: str = Field(..., min_length=1, max_length=100)
    police_station: str = Field(..., min_length=1, max_length=200)
    location_address: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=11.5, le=18.5)    # Karnataka lat range
    longitude: Optional[float] = Field(None, ge=74.0, le=78.5)   # Karnataka lon range

    # Narrative
    description: Optional[str] = None
    mo_text: Optional[str] = Field(None, description="Full MO narrative for embedding")

    # Temporal
    occurred_at: datetime

    # Optional pre-structured MO features
    mo_features: Optional[CrimeMOCreate] = None


class CrimeUpdate(BaseModel):
    crime_type: Optional[CrimeType] = None
    severity: Optional[CrimeSeverity] = None
    status: Optional[CrimeStatus] = None
    district: Optional[str] = None
    police_station: Optional[str] = None
    location_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    mo_text: Optional[str] = None
    occurred_at: Optional[datetime] = None


class CrimeResponse(BaseModel):
    id: UUID
    fir_number: str
    crime_type: CrimeType
    severity: CrimeSeverity
    status: CrimeStatus
    district: str
    police_station: str
    location_address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    description: Optional[str]
    mo_text: Optional[str]
    occurred_at: datetime
    reported_at: Optional[datetime]
    registered_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    mo_features: Optional[CrimeMOResponse] = None

    model_config = {"from_attributes": True}


class CrimeListItem(BaseModel):
    """Lightweight crime record for list views."""
    id: UUID
    fir_number: str
    crime_type: CrimeType
    severity: CrimeSeverity
    status: CrimeStatus
    district: str
    police_station: str
    occurred_at: datetime
    latitude: Optional[float]
    longitude: Optional[float]

    model_config = {"from_attributes": True}


class CrimeFilterParams(BaseModel):
    district: Optional[str] = None
    crime_type: Optional[CrimeType] = None
    status: Optional[CrimeStatus] = None
    severity: Optional[CrimeSeverity] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
