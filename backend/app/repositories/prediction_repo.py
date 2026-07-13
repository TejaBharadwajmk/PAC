"""
PAC — Prediction Repository

Handles database access for the PredictionProfile model.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prediction import PredictionProfile


class PredictionRepository:
    """Manages database access patterns for prediction snapshot profiles."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_entity(self, entity_type: str, entity_id: str) -> Optional[PredictionProfile]:
        """Fetches the latest prediction profile snapshot for a given entity."""
        stmt = (
            select(PredictionProfile)
            .where(PredictionProfile.entity_type == entity_type)
            .where(PredictionProfile.entity_id == entity_id)
            .order_by(desc(PredictionProfile.generated_at))
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def save(self, profile: PredictionProfile) -> PredictionProfile:
        """Saves a new PredictionProfile snapshot in the database."""
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_highest_risk_criminals(self, limit: int = 50, offset: int = 0) -> List[PredictionProfile]:
        """Returns the latest criminal risk forecasts ordered by risk score descending."""
        stmt = (
            select(PredictionProfile)
            .where(PredictionProfile.entity_type == "criminal")
            .where(PredictionProfile.prediction_type == "risk")
            .order_by(desc(PredictionProfile.prediction_score))
            .offset(offset)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_district_rankings(self, limit: int = 50, offset: int = 0) -> List[PredictionProfile]:
        """Returns district risk forecasts ordered by index score descending."""
        stmt = (
            select(PredictionProfile)
            .where(PredictionProfile.entity_type == "district")
            .where(PredictionProfile.prediction_type == "risk")
            .order_by(desc(PredictionProfile.prediction_score))
            .offset(offset)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_gang_rankings(self, limit: int = 50, offset: int = 0) -> List[PredictionProfile]:
        """Returns gang threat forecasts ordered by index score descending."""
        stmt = (
            select(PredictionProfile)
            .where(PredictionProfile.entity_type == "gang")
            .where(PredictionProfile.prediction_type == "threat")
            .order_by(desc(PredictionProfile.prediction_score))
            .offset(offset)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_investigation_queue(self, limit: int = 50, offset: int = 0) -> List[PredictionProfile]:
        """Returns crime case priority predictions ordered by priority score descending."""
        stmt = (
            select(PredictionProfile)
            .where(PredictionProfile.entity_type == "investigation")
            .where(PredictionProfile.prediction_type == "priority")
            .order_by(desc(PredictionProfile.prediction_score))
            .offset(offset)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_statistics(self) -> Dict[str, Any]:
        """Aggregates statistics across active predictions in prediction snapshots."""
        # Total counts
        total_stmt = select(func.count(PredictionProfile.id)).where(PredictionProfile.entity_type == "criminal")
        total = (await self.db.execute(total_stmt)).scalar_one() or 0

        # Average risk score
        avg_risk_stmt = select(func.avg(PredictionProfile.prediction_score)).where(PredictionProfile.entity_type == "criminal")
        avg_risk = (await self.db.execute(avg_risk_stmt)).scalar_one() or 0.0

        # Risk level distribution (using latest prediction for each criminal)
        # For simplicity, aggregate across the table snapshot counts
        critical_count_stmt = select(func.count(PredictionProfile.id)).where(PredictionProfile.entity_type == "criminal").where(PredictionProfile.risk_level == "CRITICAL")
        high_count_stmt = select(func.count(PredictionProfile.id)).where(PredictionProfile.entity_type == "criminal").where(PredictionProfile.risk_level == "HIGH")
        mod_count_stmt = select(func.count(PredictionProfile.id)).where(PredictionProfile.entity_type == "criminal").where(PredictionProfile.risk_level == "MODERATE")
        low_count_stmt = select(func.count(PredictionProfile.id)).where(PredictionProfile.entity_type == "criminal").where(PredictionProfile.risk_level == "LOW")

        critical = (await self.db.execute(critical_count_stmt)).scalar_one() or 0
        high = (await self.db.execute(high_count_stmt)).scalar_one() or 0
        mod = (await self.db.execute(mod_count_stmt)).scalar_one() or 0
        low = (await self.db.execute(low_count_stmt)).scalar_one() or 0

        return {
            "total_criminal_predictions": total,
            "average_criminal_risk_score": round(avg_risk, 2),
            "risk_level_distribution": {
                "low": low,
                "moderate": mod,
                "high": high,
                "critical": critical
            }
        }
