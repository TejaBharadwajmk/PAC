"""
PAC — Crime Repository

Data access layer for Crime and CrimeMO models.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.crime import Crime, CrimeMO, CrimeType, CrimeStatus, CrimeSeverity


class CrimeRepository(BaseRepository[Crime]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Crime, session)

    async def get_with_details(self, crime_id: UUID) -> Optional[Crime]:
        """Fetch a crime with all related data eagerly loaded."""
        result = await self.session.execute(
            select(Crime)
            .options(
                selectinload(Crime.mo_features),
                selectinload(Crime.crime_dna),
                selectinload(Crime.criminals),
                selectinload(Crime.victims),
            )
            .where(Crime.id == crime_id)
        )
        return result.scalar_one_or_none()

    async def get_by_fir_number(self, fir_number: str) -> Optional[Crime]:
        result = await self.session.execute(
            select(Crime).where(Crime.fir_number == fir_number)
        )
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        district: Optional[str] = None,
        crime_type: Optional[CrimeType] = None,
        status: Optional[CrimeStatus] = None,
        severity: Optional[CrimeSeverity] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Crime], int]:
        """Return (records, total_count) for paginated filtered queries."""
        conditions = []
        if district:
            conditions.append(Crime.district == district)
        if crime_type:
            conditions.append(Crime.crime_type == crime_type)
        if status:
            conditions.append(Crime.status == status)
        if severity:
            conditions.append(Crime.severity == severity)
        if from_date:
            conditions.append(Crime.occurred_at >= from_date)
        if to_date:
            conditions.append(Crime.occurred_at <= to_date)

        where_clause = and_(*conditions) if conditions else True  # type: ignore

        count_q = select(func.count()).select_from(Crime).where(where_clause)
        total = (await self.session.execute(count_q)).scalar_one()

        data_q = (
            select(Crime)
            .options(selectinload(Crime.mo_features))
            .where(where_clause)
            .order_by(Crime.occurred_at.desc())
            .offset(skip)
            .limit(limit)
        )
        crimes = list((await self.session.execute(data_q)).scalars().all())
        return crimes, total

    async def get_by_district(self, district: str, limit: int = 200) -> List[Crime]:
        result = await self.session.execute(
            select(Crime)
            .where(Crime.district == district)
            .order_by(Crime.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def crimes_without_dna(self, limit: int = 100) -> List[Crime]:
        """Return crimes that have MO text but no Crime DNA yet."""
        from app.models.crime_dna import CrimeDNA
        result = await self.session.execute(
            select(Crime)
            .outerjoin(CrimeDNA, Crime.id == CrimeDNA.crime_id)
            .where(
                Crime.mo_text.isnot(None),
                CrimeDNA.id.is_(None),
            )
            .limit(limit)
        )
        return list(result.scalars().all())
