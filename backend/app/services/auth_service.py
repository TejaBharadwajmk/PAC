"""
PAC — Authentication Service

Handles login, token refresh, and user registration business logic.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.core.exceptions import AuthenticationError, AuthorizationError, ConflictError
from app.repositories.user_repo import UserRepository
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate, TokenResponse
from app.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate(self, badge_number: str, password: str) -> TokenResponse:
        """Validate credentials and return JWT token pair."""
        user = await self.user_repo.get_by_badge(badge_number.upper())

        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Failed login attempt | badge={badge_number}")
            raise AuthenticationError("Invalid badge number or password")

        if not user.is_active:
            raise AuthenticationError(
                "Your account is deactivated. Contact your administrator."
            )

        token_data = {
            "sub": str(user.id),
            "badge": user.badge_number,
            "role": user.role.value,
        }
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        logger.info(f"Login successful | badge={badge_number} role={user.role.value}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Exchange a valid refresh token for a new access + refresh token pair."""
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise AuthenticationError("Invalid or expired refresh token")

        user = await self.user_repo.get(payload.get("sub"))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or account deactivated")

        token_data = {
            "sub": str(user.id),
            "badge": user.badge_number,
            "role": user.role.value,
        }
        return TokenResponse(
            access_token=create_access_token(data=token_data),
            refresh_token=create_refresh_token(data={"sub": str(user.id)}),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def register_user(self, data: UserCreate, created_by: User) -> User:
        """Register a new officer account. Only admins and supervisors can create users."""
        if created_by.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
            raise AuthorizationError(
                "Only supervisors and admins can register new officer accounts"
            )

        if await self.user_repo.exists_by_badge(data.badge_number):
            raise ConflictError(f"Badge number {data.badge_number!r} is already registered")

        if await self.user_repo.get_by_email(data.email):
            raise ConflictError(f"Email {data.email!r} is already registered")

        user = User(
            badge_number=data.badge_number,
            full_name=data.full_name,
            email=data.email,
            district=data.district,
            police_station=data.police_station,
            role=data.role,
            hashed_password=hash_password(data.password),
        )
        created = await self.user_repo.create(user)
        logger.info(
            f"New user registered | badge={data.badge_number} role={data.role.value} "
            f"by={created_by.badge_number}"
        )
        return created
