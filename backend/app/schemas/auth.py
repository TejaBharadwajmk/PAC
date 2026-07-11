"""
PAC — Authentication Schemas
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from app.models.user import UserRole


class LoginRequest(BaseModel):
    badge_number: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expiry


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    badge_number: str
    full_name: str
    email: EmailStr
    password: str
    district: Optional[str] = None
    police_station: Optional[str] = None
    role: UserRole = UserRole.OFFICER

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("badge_number")
    @classmethod
    def badge_format(cls, v: str) -> str:
        return v.strip().upper()


class UserResponse(BaseModel):
    id: UUID
    badge_number: str
    full_name: str
    email: str
    district: Optional[str]
    police_station: Optional[str]
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    district: Optional[str] = None
    police_station: Optional[str] = None
    is_active: Optional[bool] = None
