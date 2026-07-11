"""
PAC — Criminal Repository

Data access layer for Criminal and CrimeCriminal models.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.criminal import Criminal, CrimeCriminal


class CriminalRepository(BaseRepository[Criminal]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Criminal, session)

    async def get_with_details(self, criminal_id: UUID) -> Optional[Criminal]:
        result = await self.session.execute(
            select(Criminal)
            .options(
                selectinload(Criminal.crimes),
                selectinload(Criminal.behaviour_profile),
            )
            .where(Criminal.id == criminal_id)
        )
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str, limit: int = 20) -> List[Criminal]:
        result = await self.session.execute(
            select(Criminal)
            .where(Criminal.name.ilike(f"%{name}%"))
            .order_by(Criminal.name)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_repeat_offenders(
        self, district: Optional[str] = None, limit: int = 50
    ) -> List[Criminal]:
        query = (
            select(Criminal)
            .where(Criminal.is_repeat_offender == True)
        )
        if district:
            query = query.where(Criminal.district == district)
        query = query.order_by(Criminal.previous_cases_count.desc()).limit(limit)
        return list((await self.session.execute(query)).scalars().all())

    async def get_wanted(self, limit: int = 50) -> List[Criminal]:
        result = await self.session.execute(
            select(Criminal)
            .where(Criminal.is_wanted == True)
            .order_by(Criminal.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_crimes_for_criminal(self, criminal_id: UUID) -> List[CrimeCriminal]:
        result = await self.session.execute(
            select(CrimeCriminal)
            .options(selectinload(CrimeCriminal.crime))
            .where(CrimeCriminal.criminal_id == criminal_id)
            .order_by(CrimeCriminal.created_at.desc())
        )
        return list(result.scalars().all())
