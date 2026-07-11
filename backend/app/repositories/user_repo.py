"""
PAC — User Repository

Data access layer for User model.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_badge(self, badge_number: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.badge_number == badge_number)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def exists_by_badge(self, badge_number: str) -> bool:
        result = await self.session.execute(
            select(User).where(User.badge_number == badge_number)
        )
        return result.scalar_one_or_none() is not None
