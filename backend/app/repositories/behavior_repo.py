"""
PAC — Behavior Repository

Handles database operations for the BehaviourProfile model.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.behaviour import BehaviourProfile
from app.models.criminal import Criminal


class BehaviorRepository:
    """Manages database access patterns for behaviour intelligence profiles."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_criminal_id(self, criminal_id: UUID) -> Optional[BehaviourProfile]:
        """Fetches the BehaviourProfile for a criminal, eager-loading the criminal profile."""
        stmt = select(BehaviourProfile).options(
            selectinload(BehaviourProfile.criminal)
        ).where(BehaviourProfile.criminal_id == criminal_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def save(self, profile: BehaviourProfile) -> BehaviourProfile:
        """Saves or updates a BehaviourProfile in the database."""
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_high_risk(self, limit: int = 50, offset: int = 0) -> List[BehaviourProfile]:
        """Returns behaviour profiles ordered by risk score descending."""
        stmt = select(BehaviourProfile).options(
            selectinload(BehaviourProfile.criminal)
        ).order_by(desc(BehaviourProfile.risk_score)).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_repeat_offenders(self, limit: int = 50, offset: int = 0) -> List[BehaviourProfile]:
        """Returns behaviour profiles ordered by repeat offender score descending."""
        stmt = select(BehaviourProfile).options(
            selectinload(BehaviourProfile.criminal)
        ).order_by(desc(BehaviourProfile.repeat_offender_score)).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_serial_patterns(self, min_consistency: float = 0.6, limit: int = 50, offset: int = 0) -> List[BehaviourProfile]:
        """Returns profiles matching a minimum behavior consistency threshold."""
        stmt = select(BehaviourProfile).options(
            selectinload(BehaviourProfile.criminal)
        ).where(BehaviourProfile.behaviour_consistency_score >= min_consistency).order_by(
            desc(BehaviourProfile.behaviour_consistency_score)
        ).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_statistics(self) -> Dict[str, Any]:
        """Calculates aggregated overview statistics across all behavior profiles."""
        stmt = select(
            func.count(BehaviourProfile.id),
            func.avg(BehaviourProfile.risk_score),
            func.avg(BehaviourProfile.behaviour_consistency_score),
            func.avg(BehaviourProfile.operating_radius_km)
        )
        res = await self.db.execute(stmt)
        total, avg_risk, avg_consistency, avg_radius = res.first() or (0, 0.0, 0.0, 0.0)

        # Risk distribution counts
        low_count_stmt = select(func.count(BehaviourProfile.id)).where(BehaviourProfile.risk_level == "LOW")
        med_count_stmt = select(func.count(BehaviourProfile.id)).where(BehaviourProfile.risk_level == "MEDIUM")
        high_count_stmt = select(func.count(BehaviourProfile.id)).where(BehaviourProfile.risk_level == "HIGH")

        low_count = (await self.db.execute(low_count_stmt)).scalar_one() or 0
        med_count = (await self.db.execute(med_count_stmt)).scalar_one() or 0
        high_count = (await self.db.execute(high_count_stmt)).scalar_one() or 0

        return {
            "total_profiles": total,
            "average_risk_score": round(avg_risk or 0.0, 2),
            "average_consistency_score": round(avg_consistency or 0.0, 2),
            "average_operating_radius_km": round(avg_radius or 0.0, 2),
            "risk_level_distribution": {
                "low": low_count,
                "medium": med_count,
                "high": high_count
            }
        }
