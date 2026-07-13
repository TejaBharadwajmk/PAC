"""
PAC — CrimeDNA Repository

All database operations for the crime_dna table, including:
  - CRUD + status lifecycle management
  - pgvector cosine similarity ANN search with pre-filtering
  - Pipeline statistics queries
  - Startup sweep for abandoned PENDING/PROCESSING records
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, text, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crime_dna import CrimeDNA, DNAStatus
from app.models.crime import Crime

logger = logging.getLogger(__name__)


class DNARepository:
    """Repository for CrimeDNA pgvector operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Read ───────────────────────────────────────────────

    async def get_by_crime_id(self, crime_id: UUID) -> Optional[CrimeDNA]:
        """Fetch the CrimeDNA record for a given crime."""
        result = await self.session.execute(
            select(CrimeDNA).where(CrimeDNA.crime_id == crime_id)
        )
        return result.scalar_one_or_none()

    async def exists(self, crime_id: UUID) -> bool:
        result = await self.session.execute(
            select(CrimeDNA.id).where(CrimeDNA.crime_id == crime_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_recoverable(self, limit: int = 100) -> List[CrimeDNA]:
        """
        Return PENDING and FAILED records for startup recovery sweep.
        PROCESSING records older than 5 minutes are also included
        (they crashed mid-task and should be retried).
        """
        from sqlalchemy import or_
        result = await self.session.execute(
            select(CrimeDNA)
            .where(
                or_(
                    CrimeDNA.status == DNAStatus.PENDING.value,
                    CrimeDNA.status == DNAStatus.FAILED.value,
                )
            )
            .order_by(CrimeDNA.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Write ──────────────────────────────────────────────

    async def create_pending(
        self,
        crime_id: UUID,
        *,
        crime_type: Optional[str] = None,
        district: Optional[str] = None,
        police_station: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        # Time intelligence (precomputed by caller)
        hour_of_day: Optional[int] = None,
        day_of_week: Optional[int] = None,
        is_weekend: Optional[bool] = None,
        is_night: Optional[bool] = None,
        time_of_day_slot: Optional[str] = None,
        month: Optional[int] = None,
    ) -> CrimeDNA:
        """
        Create a PENDING CrimeDNA record at crime registration time.
        Fills in all available intelligence fields immediately;
        embedding is filled later by the background task.
        """
        dna = CrimeDNA(
            crime_id=crime_id,
            status=DNAStatus.PENDING,
            crime_type=crime_type,
            district=district,
            police_station=police_station,
            latitude=latitude,
            longitude=longitude,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            is_weekend=is_weekend,
            is_night=is_night,
            time_of_day_slot=time_of_day_slot,
            month=month,
        )
        self.session.add(dna)
        await self.session.flush()
        logger.debug(f"CrimeDNA PENDING created | crime_id={crime_id}")
        return dna

    async def mark_processing(self, crime_id: UUID) -> Optional[CrimeDNA]:
        """Transition status to PROCESSING and record start time."""
        dna = await self.get_by_crime_id(crime_id)
        if dna is None:
            return None
        dna.status = DNAStatus.PROCESSING
        dna.processing_started_at = datetime.now(timezone.utc)
        await self.session.flush()
        return dna

    async def mark_completed(
        self,
        crime_id: UUID,
        *,
        embedding: List[float],
        mo_text_embedded: str,
        model_name: str = "all-MiniLM-L6-v2",
        # Structured MO (denormalized from crime_mo)
        crime_method: Optional[str] = None,
        target_type: Optional[str] = None,
        weapon_used: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        planning_level: Optional[str] = None,
        gang_involved: bool = False,
        escape_method: Optional[str] = None,
        modus_operandi_tags: Optional[List[str]] = None,
    ) -> Optional[CrimeDNA]:
        """
        Store the embedding and all intelligence fields, transition to COMPLETED.
        """
        dna = await self.get_by_crime_id(crime_id)
        if dna is None:
            return None

        dna.status            = DNAStatus.COMPLETED
        dna.status_message    = None
        dna.embedding         = embedding          # type: ignore[assignment]
        dna.mo_text_embedded  = mo_text_embedded
        dna.model_name        = model_name
        dna.generated_at      = datetime.now(timezone.utc)

        # Denormalized MO intelligence
        dna.crime_method        = crime_method
        dna.target_type         = target_type
        dna.weapon_used         = weapon_used
        dna.tools_used          = tools_used or []
        dna.planning_level      = planning_level
        dna.gang_involved       = gang_involved
        dna.escape_method       = escape_method
        dna.modus_operandi_tags = modus_operandi_tags or []

        await self.session.flush()
        logger.info(f"CrimeDNA COMPLETED | crime_id={crime_id}")
        return dna

    async def mark_failed(
        self,
        crime_id: UUID,
        error_message: str,
        retry_count: int,
    ) -> Optional[CrimeDNA]:
        """Record a generation failure."""
        dna = await self.get_by_crime_id(crime_id)
        if dna is None:
            return None
        dna.status               = DNAStatus.FAILED
        dna.status_message       = error_message[:1000]  # cap length
        dna.retry_count          = retry_count
        dna.processing_failed_at = datetime.now(timezone.utc)
        await self.session.flush()
        logger.error(f"CrimeDNA FAILED | crime_id={crime_id} | retries={retry_count} | {error_message}")
        return dna

    async def reset_for_reindex(self, crime_id: UUID) -> Optional[CrimeDNA]:
        """Reset a FAILED or COMPLETED record back to PENDING for reindexing."""
        dna = await self.get_by_crime_id(crime_id)
        if dna is None:
            return None
        dna.status          = DNAStatus.PENDING
        dna.status_message  = "Reindex requested"
        dna.retry_count     = 0
        dna.embedding       = None  # type: ignore[assignment]
        dna.generated_at    = None
        await self.session.flush()
        return dna

    # ── Similarity Search ──────────────────────────────────

    async def find_similar(
        self,
        query_embedding: List[float],
        *,
        exclude_crime_id: Optional[UUID] = None,
        limit: int = 50,             # over-fetch for Python re-ranking
        max_distance: float = 0.50,  # 1.0 - min_similarity
        district_filter: Optional[str] = None,
        crime_type_filter: Optional[str] = None,
        time_slot_filter: Optional[str] = None,
    ) -> List[Tuple[dict, float]]:
        """
        Phase 2 of hybrid search: pgvector ANN cosine similarity.

        Returns list of (row_dict, semantic_similarity) pairs, sorted
        best-first. Caller (SimilarityService) applies Phase 3 re-ranking.

        Args:
            query_embedding: L2-normalised 384-dim vector
            exclude_crime_id: Skip this crime (the source crime)
            limit: Number of ANN candidates to fetch (over-fetch ×5 of final)
            max_distance: cosine DISTANCE threshold (1 - min_similarity)
            district_filter: Optional WHERE district =
            crime_type_filter: Optional WHERE crime_type =
            time_slot_filter: Optional WHERE time_of_day_slot =
        """
        conditions = ["d.status = 'completed'", "d.embedding IS NOT NULL"]
        params: dict = {
            "embedding": str(query_embedding),
            "max_distance": max_distance,
            "limit": limit,
        }

        if exclude_crime_id:
            conditions.append("d.crime_id != :exclude_id")
            params["exclude_id"] = str(exclude_crime_id)

        if district_filter:
            conditions.append("d.district = :district")
            params["district"] = district_filter

        if crime_type_filter:
            conditions.append("d.crime_type = :crime_type")
            params["crime_type"] = crime_type_filter

        if time_slot_filter:
            conditions.append("d.time_of_day_slot = :time_slot")
            params["time_slot"] = time_slot_filter

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT
                d.crime_id,
                d.crime_type,
                d.crime_method,
                d.target_type,
                d.weapon_used,
                d.tools_used,
                d.planning_level,
                d.gang_involved,
                d.escape_method,
                d.modus_operandi_tags,
                d.time_of_day_slot,
                d.hour_of_day,
                d.is_night,
                d.district,
                d.police_station,
                d.latitude,
                d.longitude,
                c.fir_number,
                c.severity,
                c.status    AS crime_status,
                c.mo_text,
                c.occurred_at,
                (1 - (d.embedding <=> CAST(:embedding AS vector))) AS semantic_similarity
            FROM crime_dna d
            JOIN crimes c ON d.crime_id = c.id
            WHERE {where_clause}
              AND (d.embedding <=> CAST(:embedding AS vector)) <= :max_distance
            ORDER BY d.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        result = await self.session.execute(sql, params)
        rows = result.mappings().fetchall()

        return [
            (dict(row), float(row["semantic_similarity"]))
            for row in rows
        ]

    # ── Stats ──────────────────────────────────────────────

    async def get_pipeline_stats(self) -> dict:
        """Count records by status for the admin stats endpoint."""
        result = await self.session.execute(
            select(CrimeDNA.status, func.count().label("n"))
            .group_by(CrimeDNA.status)
        )
        counts = {str(row.status).lower(): row.n for row in result}
        total = sum(counts.values())
        completed = counts.get("completed", 0)
        return {
            "total_crimes": total,
            "pending":    counts.get("pending",    0),
            "processing": counts.get("processing", 0),
            "completed":  completed,
            "failed":     counts.get("failed",     0),
            "completion_rate_pct": round(completed / total * 100, 1) if total else 0.0,
        }
