"""
PAC — Geo Intelligence Repository
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.crime import Crime


class GeoRepository(BaseRepository[Crime]):
    """Repository for PostGIS DBSCAN spatial queries and hotspots."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Crime, session)

    async def get_dbscan_hotspots(
        self,
        eps: float,
        min_samples: int,
        district: Optional[str] = None,
        crime_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs PostGIS ST_ClusterDBSCAN on crimes table to identify hotspots.
        Geometries are transformed to EPSG:3857 (meters) for accurate radius thresholding.
        """
        query = text("""
            WITH clustered_crimes AS (
                SELECT
                    c.id,
                    c.crime_type,
                    c.occurred_at,
                    c.district,
                    c.police_station,
                    c.latitude,
                    c.longitude,
                    c.geom,
                    ST_ClusterDBSCAN(ST_Transform(c.geom, 3857), eps := :eps, minpoints := :min_samples) OVER () AS cluster_id
                FROM crimes c
                WHERE c.geom IS NOT NULL
                  AND (CAST(:district AS VARCHAR) IS NULL OR c.district = :district)
                  AND (CAST(:crime_type AS VARCHAR) IS NULL OR c.crime_type = CAST(:crime_type AS crime_type))
                  AND (CAST(:start_date AS TIMESTAMPTZ) IS NULL OR c.occurred_at >= :start_date)
                  AND (CAST(:end_date AS TIMESTAMPTZ) IS NULL OR c.occurred_at <= :end_date)
            ),
            cluster_centers AS (
                SELECT
                    cc.cluster_id,
                    ST_Centroid(ST_Collect(cc.geom)) AS center_geom,
                    COUNT(*) AS crime_count,
                    ARRAY_AGG(cc.id) AS crime_ids
                FROM clustered_crimes cc
                WHERE cc.cluster_id IS NOT NULL
                GROUP BY cc.cluster_id
            )
            SELECT
                ct.cluster_id,
                ct.crime_count,
                ST_Y(ct.center_geom) AS center_latitude,
                ST_X(ct.center_geom) AS center_longitude,
                COALESCE(MAX(ST_Distance(geography(cc.geom), geography(ct.center_geom))), 0.0) AS radius_meters,
                ct.crime_ids
            FROM cluster_centers ct
            JOIN clustered_crimes cc ON ct.cluster_id = cc.cluster_id
            GROUP BY ct.cluster_id, ct.crime_count, ct.center_geom, ct.crime_ids
            ORDER BY ct.crime_count DESC;
        """)

        result = await self.session.execute(
            query,
            {
                "eps": eps,
                "min_samples": min_samples,
                "district": district,
                "crime_type": crime_type,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        hotspots = []
        for row in result.all():
            hotspots.append({
                "cluster_id": row.cluster_id,
                "crime_count": row.crime_count,
                "center_latitude": row.center_latitude,
                "center_longitude": row.center_longitude,
                "radius_meters": float(row.radius_meters),
                "crime_ids": row.crime_ids,
            })
        return hotspots

    async def get_total_spatial_crimes(
        self,
        district: Optional[str] = None,
        crime_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Counts all crimes with valid geometries matching the optional filters."""
        query = text("""
            SELECT COUNT(*)
            FROM crimes
            WHERE geom IS NOT NULL
              AND (CAST(:district AS VARCHAR) IS NULL OR district = :district)
              AND (CAST(:crime_type AS VARCHAR) IS NULL OR crime_type = CAST(:crime_type AS crime_type))
              AND (CAST(:start_date AS TIMESTAMPTZ) IS NULL OR occurred_at >= :start_date)
              AND (CAST(:end_date AS TIMESTAMPTZ) IS NULL OR occurred_at <= :end_date);
        """)
        result = await self.session.execute(
            query,
            {
                "district": district,
                "crime_type": crime_type,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return result.scalar_one()

    async def get_cluster_criminals_and_mo_details(
        self,
        crime_ids: List[uuid.UUID],
    ) -> Dict[str, Any]:
        """
        Fetches detailed statistics for a specific list of crime IDs, including:
        - Distinct repeat offenders count
        - Distinct gang count
        - Occurred timestamps (for trend analysis)
        - Dominant crime types (with frequency)
        - Peak MO time of day slots (with frequency)
        """
        if not crime_ids:
            return {
                "repeat_offenders_count": 0,
                "known_gangs_count": 0,
                "occurred_timestamps": [],
                "crime_types": {},
                "time_slots": {},
            }

        # 1. Query repeat offenders count
        ro_query = text("""
            SELECT COUNT(DISTINCT cc.criminal_id)
            FROM crime_criminals cc
            JOIN criminals c ON cc.criminal_id = c.id
            WHERE cc.crime_id = ANY(:crime_ids)
              AND c.is_repeat_offender = true;
        """)
        ro_result = await self.session.execute(ro_query, {"crime_ids": crime_ids})
        repeat_offenders_count = ro_result.scalar_one()

        # 2. Query distinct gang names count
        gang_query = text("""
            SELECT COUNT(DISTINCT c.gang_name)
            FROM crime_criminals cc
            JOIN criminals c ON cc.criminal_id = c.id
            WHERE cc.crime_id = ANY(:crime_ids)
              AND c.gang_affiliation = true
              AND c.gang_name IS NOT NULL
              AND c.gang_name <> '';
        """)
        gang_result = await self.session.execute(gang_query, {"crime_ids": crime_ids})
        known_gangs_count = gang_result.scalar_one()

        # 3. Fetch crime details: occurred_at, crime_type
        crimes_query = text("""
            SELECT id, crime_type, occurred_at
            FROM crimes
            WHERE id = ANY(:crime_ids);
        """)
        crimes_result = await self.session.execute(crimes_query, {"crime_ids": crime_ids})
        
        occurred_timestamps = []
        crime_types = {}
        for row in crimes_result.all():
            occurred_timestamps.append(row.occurred_at)
            c_type = str(row.crime_type)
            crime_types[c_type] = crime_types.get(c_type, 0) + 1

        # 4. Fetch MO time slots
        mo_query = text("""
            SELECT time_of_day, COUNT(*) as slot_count
            FROM crime_mo
            WHERE crime_id = ANY(:crime_ids)
              AND time_of_day IS NOT NULL
            GROUP BY time_of_day;
        """)
        mo_result = await self.session.execute(mo_query, {"crime_ids": crime_ids})
        
        time_slots = {}
        for row in mo_result.all():
            time_slots[row.time_of_day] = row.slot_count

        return {
            "repeat_offenders_count": repeat_offenders_count,
            "known_gangs_count": known_gangs_count,
            "occurred_timestamps": occurred_timestamps,
            "crime_types": crime_types,
            "time_slots": time_slots,
        }

    async def get_top_hot_district(self) -> Optional[str]:
        """Gets the district with the highest density of spatial crimes."""
        query = text("""
            SELECT district, COUNT(*) as c_count
            FROM crimes
            WHERE geom IS NOT NULL
            GROUP BY district
            ORDER BY c_count DESC
            LIMIT 1;
        """)
        result = await self.session.execute(query)
        row = result.first()
        return row[0] if row else None
