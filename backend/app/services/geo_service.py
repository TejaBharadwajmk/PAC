"""
PAC — Geo Intelligence Service
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.geo_repo import GeoRepository
from app.services.recommendation_engine import RecommendationEngine
from app.schemas.geo import HotspotResponse, GeoStatisticsResponse

logger = logging.getLogger(__name__)


class GeoService:
    """Coordinates spatial queries, hotspot trend calculations, and recommendations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GeoRepository(db)

    async def get_hotspots(
        self,
        eps: float = 1000.0,
        min_samples: int = 5,
        district: Optional[str] = None,
        crime_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[HotspotResponse]:
        """
        Calculates and returns enriched hotspots.
        Includes trend analysis, suggested patrol windows, and AI recommendation directives.
        """
        # 1. Fetch DBSCAN clusters from database
        clusters = await self.repo.get_dbscan_hotspots(
            eps=eps,
            min_samples=min_samples,
            district=district,
            crime_type=crime_type,
            start_date=start_date,
            end_date=end_date,
        )

        hotspots = []
        for c in clusters:
            crime_ids = c["crime_ids"]
            
            # 2. Query detailed offender and MO attributes for cluster crime_ids
            details = await self.repo.get_cluster_criminals_and_mo_details(crime_ids)
            
            # 3. Determine dominant crime type
            dominant_crime_type = crime_type
            if not dominant_crime_type and details["crime_types"]:
                # Pick the crime type with highest frequency
                dominant_crime_type = max(details["crime_types"], key=details["crime_types"].get)
            if not dominant_crime_type:
                dominant_crime_type = "other"

            # 4. Determine peak time slot
            peak_time = "unknown"
            if details["time_slots"]:
                peak_time = max(details["time_slots"], key=details["time_slots"].get)
            
            # 5. Calculate suggested patrol window (pad by 30 mins)
            suggested_patrol_window = self._get_suggested_patrol_window(peak_time)

            # 6. Trend Analysis (Chronological splitting of hotspot incidents)
            hotspot_trend = self._calculate_trend(details["occurred_timestamps"])

            # 7. Risk Level Assessment
            repeat_offenders = details["repeat_offenders_count"]
            known_gangs = details["known_gangs_count"]
            crime_count = c["crime_count"]
            radius_meters = c["radius_meters"]

            risk_level = "Low"
            if crime_count >= 10 or repeat_offenders >= 2 or known_gangs >= 1:
                risk_level = "High"
            elif crime_count >= 5 or repeat_offenders >= 1:
                risk_level = "Medium"

            # 8. Confidence Score calculation
            confidence_score = 0.0
            if crime_count > 0:
                # Dense, high-volume clusters yield score approaching 1.0
                confidence_score = min(1.0, (crime_count / 10.0) * (500.0 / max(50.0, radius_meters)))
                confidence_score = round(confidence_score, 2)

            # 9. Invoke stand-alone Recommendation Engine
            recommendation = RecommendationEngine.generate_recommendation(
                dominant_crime_type=dominant_crime_type,
                peak_time=peak_time,
                risk_level=risk_level,
                repeat_offenders_count=repeat_offenders,
                known_gangs_count=known_gangs,
                crime_count=crime_count,
                hotspot_trend=hotspot_trend,
            )

            hotspots.append(
                HotspotResponse(
                    cluster_id=c["cluster_id"],
                    center_latitude=c["center_latitude"],
                    center_longitude=c["center_longitude"],
                    radius_meters=radius_meters,
                    crime_count=crime_count,
                    dominant_crime_type=dominant_crime_type,
                    peak_time=peak_time,
                    suggested_patrol_window=suggested_patrol_window,
                    hotspot_trend=hotspot_trend,
                    confidence_score=confidence_score,
                    risk_level=risk_level,
                    repeat_offenders_count=repeat_offenders,
                    known_gangs_count=known_gangs,
                    recommendation=recommendation,
                )
            )

        # Trigger predictive calculations updates for the district/hotspots
        try:
            from app.services.prediction_service import PredictionService
            pred_svc = PredictionService(self.db)
            import asyncio
            if district:
                asyncio.ensure_future(pred_svc.generate_district_prediction(district))
            asyncio.ensure_future(pred_svc.generate_hotspot_predictions())
        except Exception as e:
            logger.error(f"Failed to trigger district/hotspot prediction updates: {e}")

        return hotspots

    async def get_statistics(
        self,
        eps: float = 1000.0,
        min_samples: int = 5,
        district: Optional[str] = None,
        crime_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> GeoStatisticsResponse:
        """Generates general geo statistics and aggregate performance summaries."""
        # 1. Fetch hotspots
        hotspots = await self.get_hotspots(
            eps=eps,
            min_samples=min_samples,
            district=district,
            crime_type=crime_type,
            start_date=start_date,
            end_date=end_date,
        )

        # 2. Get total crimes analyzed with geometries
        total_crimes_analyzed = await self.repo.get_total_spatial_crimes(
            district=district,
            crime_type=crime_type,
            start_date=start_date,
            end_date=end_date,
        )

        total_hotspots_detected = len(hotspots)
        total_clustered_crimes = sum(h.crime_count for h in hotspots)
        total_noise_crimes = max(0, total_crimes_analyzed - total_clustered_crimes)

        # 3. Calculate average hotspot radius
        avg_radius = 0.0
        if total_hotspots_detected > 0:
            avg_radius = sum(h.radius_meters for h in hotspots) / total_hotspots_detected
            avg_radius = round(avg_radius, 2)

        # 4. Get top hotspot district
        top_hotspot_district = await self.repo.get_top_hot_district()

        # 5. Get highest risk hotspot cluster ID (first element since they are sorted DESC by count)
        highest_risk_hotspot_id = None
        if hotspots:
            highest_risk_hotspot_id = hotspots[0].cluster_id

        return GeoStatisticsResponse(
            total_crimes_analyzed=total_crimes_analyzed,
            total_hotspots_detected=total_hotspots_detected,
            total_clustered_crimes=total_clustered_crimes,
            total_noise_crimes=total_noise_crimes,
            top_hotspot_district=top_hotspot_district,
            average_hotspot_radius_meters=avg_radius,
            highest_risk_hotspot_id=highest_risk_hotspot_id,
        )

    def _calculate_trend(self, occurred_timestamps: List[datetime]) -> str:
        """
        Classifies trend as Emerging, Stable, or Declining.
        Splits timestamps chronologically into first and second halves.
        """
        timestamps = sorted(occurred_timestamps)
        if len(timestamps) < 3:
            return "Stable"

        # Calculate time span midpoint
        t_min, t_max = timestamps[0], timestamps[-1]
        if t_min == t_max:
            return "Stable"

        midpoint = t_min + (t_max - t_min) / 2
        
        first_half = [t for t in timestamps if t <= midpoint]
        second_half = [t for t in timestamps if t > midpoint]

        if len(second_half) > len(first_half):
            return "Emerging"
        elif len(second_half) < len(first_half):
            return "Declining"
        else:
            return "Stable"

    def _get_suggested_patrol_window(self, peak_time: str) -> str:
        """Returns suggested patrol window padding peak hours by 30 mins."""
        mapping = {
            "morning": "05:30-12:30",
            "afternoon": "11:30-18:30",
            "evening": "17:30-22:30",
            "night": "21:30-02:30",
            "late_night": "01:30-06:30",
        }
        return mapping.get(peak_time.lower(), "24-hour dynamic patrols recommended")
