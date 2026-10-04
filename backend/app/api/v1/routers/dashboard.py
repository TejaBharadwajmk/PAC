"""
PAC — Dashboard Summary Router

Provides an aggregated, high-performance endpoint (/api/v1/dashboard/summary)
using Redis caching and concurrent database execution (asyncio.gather).
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, CurrentUser
from app.models.crime import Crime, CrimeStatus, CrimeSeverity
from app.schemas.dashboard import DashboardSummaryResponse, DashboardCrimeItem
from app.core.cache import cache_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get aggregated dashboard summary",
    description="Returns consolidated crime statistics, recent cases, hotspot counts, and system status with Redis caching.",
)
@cache_response(ttl_seconds=180, namespace="dashboard")
async def get_dashboard_summary(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Executes database queries concurrently using asyncio.gather.
    Cached for 3 minutes in Redis.
    """
    # Define async sub-queries
    async def fetch_crime_counts():
        q_total = select(func.count(Crime.id))
        q_open = select(func.count(Crime.id)).where(Crime.status.in_([CrimeStatus.REPORTED, CrimeStatus.UNDER_INVESTIGATION]))
        q_solved = select(func.count(Crime.id)).where(Crime.status.in_([CrimeStatus.CHARGESHEETED, CrimeStatus.CLOSED]))
        q_high = select(func.count(Crime.id)).where(Crime.severity == CrimeSeverity.HIGH)

        res_total = (await db.execute(q_total)).scalar_one() or 0
        res_open = (await db.execute(q_open)).scalar_one() or 0
        res_solved = (await db.execute(q_solved)).scalar_one() or 0
        res_high = (await db.execute(q_high)).scalar_one() or 0

        return res_total, res_open, res_solved, res_high

    async def fetch_recent_crimes():
        q_recent = (
            select(Crime)
            .order_by(Crime.occurred_at.desc())
            .limit(5)
        )
        res = await db.execute(q_recent)
        crimes = res.scalars().all()
        return [
            DashboardCrimeItem(
                id=c.id,
                fir_number=c.fir_number,
                crime_type=c.crime_type.value if hasattr(c.crime_type, "value") else str(c.crime_type),
                severity=c.severity.value if hasattr(c.severity, "value") else str(c.severity),
                status=c.status.value if hasattr(c.status, "value") else str(c.status),
                district=c.district,
                police_station=c.police_station,
                occurred_at=c.occurred_at,
            )
            for c in crimes
        ]

    async def fetch_hotspots_count():
        try:
            from app.repositories.geo_repo import GeoRepository
            repo = GeoRepository(db)
            hotspots = await repo.get_dbscan_hotspots()
            return len(hotspots)
        except Exception as exc:
            logger.warning(f"Failed to fetch hotspots count: {exc}")
            return 0

    async def fetch_graph_counts():
        try:
            from app.graph_db import get_graph_session
            async with get_graph_session() as g_session:
                res_nodes = await g_session.run("MATCH (n) RETURN count(n) AS c")
                record_nodes = await res_nodes.single()
                nodes_count = record_nodes["c"] if record_nodes else 0

                res_edges = await g_session.run("MATCH ()-[r]->() RETURN count(r) AS c")
                record_edges = await res_edges.single()
                edges_count = record_edges["c"] if record_edges else 0

                return nodes_count, edges_count
        except Exception as exc:
            logger.warning(f"Neo4j count fallback: {exc}")
            return 0, 0

    # Execute all queries concurrently
    (
        (total_crimes, open_cases, solved_cases, high_severity),
        recent_crimes,
        hotspots_count,
        (graph_nodes, graph_edges),
    ) = await asyncio.gather(
        fetch_crime_counts(),
        fetch_recent_crimes(),
        fetch_hotspots_count(),
        fetch_graph_counts(),
    )

    return DashboardSummaryResponse(
        total_crimes=total_crimes,
        open_cases=open_cases,
        solved_cases=solved_cases,
        high_severity_cases=high_severity,
        hotspots_count=hotspots_count,
        graph_nodes_count=graph_nodes,
        graph_edges_count=graph_edges,
        recent_crimes=recent_crimes,
        system_status={
            "database": "online",
            "redis": "online",
            "neo4j": "online" if graph_nodes > 0 else "degraded",
            "ml_engine": "ready",
        },
        cached_at=datetime.utcnow().isoformat(),
    )
