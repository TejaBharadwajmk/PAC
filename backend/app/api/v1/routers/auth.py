"""
PAC — Authentication Router

Endpoints:
  POST /api/v1/auth/login      — Authenticate with badge + password
  POST /api/v1/auth/refresh    — Refresh access token
  GET  /api/v1/auth/me         — Get current user profile
  POST /api/v1/auth/register   — Create new officer (supervisor/admin only)
"""

from fastapi import APIRouter, status

from app.dependencies import DbSession, CurrentUser
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    UserCreate, UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Officer login",
    description="Authenticate using badge number and password. Returns JWT access and refresh tokens.",
)
async def login(request: LoginRequest, db: DbSession):
    service = AuthService(db)
    return await service.authenticate(request.badge_number, request.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(request: RefreshRequest, db: DbSession):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    service = AuthService(db)
    return await service.refresh_access_token(request.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user profile",
)
async def get_current_user(current_user: CurrentUser):
    """Return the profile of the currently authenticated officer."""
    return current_user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new officer",
    description="Create a new officer account. Requires supervisor or admin role.",
)
async def register_officer(
    data: UserCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    service = AuthService(db)
    return await service.register_user(data, current_user)
