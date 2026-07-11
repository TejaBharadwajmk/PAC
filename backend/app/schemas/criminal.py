"""
PAC — Criminal Schemas (Pydantic v2)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from app.models.criminal import CrimeRole


class CriminalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    aliases: List[str] = Field(default_factory=list)
    date_of_birth: Optional[date] = None
    age: Optional[int] = Field(None, ge=10, le=100)
    gender: str = "male"
    district: Optional[str] = None
    state: str = "Karnataka"
    address: Optional[str] = None
    contact_number: Optional[str] = None
    gang_name: Optional[str] = None
    gang_affiliation: bool = False
    height_cm: Optional[int] = Field(None, ge=100, le=250)
    build: Optional[str] = None
    identifying_marks: Optional[str] = None
    is_wanted: bool = False


class CriminalUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    age: Optional[int] = None
    district: Optional[str] = None
    address: Optional[str] = None
    contact_number: Optional[str] = None
    gang_name: Optional[str] = None
    gang_affiliation: Optional[bool] = None
    is_wanted: Optional[bool] = None
    is_arrested: Optional[bool] = None
    identifying_marks: Optional[str] = None


class CriminalResponse(BaseModel):
    id: UUID
    name: str
    aliases: List[str]
    date_of_birth: Optional[date]
    age: Optional[int]
    gender: str
    district: Optional[str]
    state: str
    address: Optional[str]
    is_repeat_offender: bool
    previous_cases_count: int
    gang_name: Optional[str]
    gang_affiliation: bool
    is_wanted: bool
    is_arrested: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CriminalListItem(BaseModel):
    id: UUID
    name: str
    aliases: List[str]
    district: Optional[str]
    is_repeat_offender: bool
    gang_name: Optional[str]
    is_wanted: bool
    previous_cases_count: int

    model_config = {"from_attributes": True}


class AssignCriminalToCrime(BaseModel):
    criminal_id: UUID
    role: CrimeRole = CrimeRole.ACCUSED
    notes: Optional[str] = None
