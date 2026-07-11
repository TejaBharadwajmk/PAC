"""
PAC — Victim Schemas (Pydantic v2)
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class VictimCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    occupation: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    contact_number: Optional[str] = None


class VictimResponse(BaseModel):
    id: UUID
    name: str
    age: Optional[int]
    gender: Optional[str]
    occupation: Optional[str]
    district: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AddVictimToCrime(BaseModel):
    victim_id: UUID
    injury_type: str = Field(default="none", pattern="^(none|minor|major|fatal)$")
    loss_amount: Optional[Decimal] = Field(None, ge=0)
    loss_description: Optional[str] = None
