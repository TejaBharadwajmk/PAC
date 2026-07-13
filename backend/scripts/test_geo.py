"""
PAC Backend — Geo Intelligence Unit Tests
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.crime import CrimeType
from app.schemas.geo import HotspotResponse, GeoStatisticsResponse
from app.services.recommendation_engine import RecommendationEngine
from app.services.geo_service import GeoService

# Create FastAPI TestClient
client = TestClient(app)

MOCK_USER_ID = uuid4()
MOCK_OFFICER = User(
    id=MOCK_USER_ID,
    badge_number="OFF001",
    full_name="HC Ravi Kumar",
    email="off001@ksp.gov.in",
    district="Bengaluru Urban",
    role=UserRole.OFFICER,
    is_active=True,
)


class TestGeoIntelligence(unittest.TestCase):

    def setUp(self):
        # Override db session dependency and auth dependency
        self.db_mock = AsyncMock()
        app.dependency_overrides[get_db_session] = lambda: self.db_mock
        app.dependency_overrides[get_current_user] = lambda: MOCK_OFFICER

    def tearDown(self):
        app.dependency_overrides.clear()

    # ─────────────────────────────────────────────────────────
    # 1. RECOMMENDATION ENGINE TESTS
    # ─────────────────────────────────────────────────────────

    def test_recommendation_engine_high_risk_burglary(self):
        rec = RecommendationEngine.generate_recommendation(
            dominant_crime_type="burglary",
            peak_time="night",
            risk_level="High",
            repeat_offenders_count=2,
            known_gangs_count=1,
            crime_count=12,
            hotspot_trend="Emerging",
        )
        # Verify recommendation contains correct rule-based operational advice
        self.assertIn("burglary", rec.lower())
        self.assertIn("night", rec)
        self.assertIn("High-Risk", rec)
        self.assertIn("additional patrol vehicle", rec)
        self.assertIn("repeat offenders", rec)
        self.assertIn("gang networks", rec)
        self.assertIn("Emerging", rec)

    def test_recommendation_engine_low_risk_theft(self):
        rec = RecommendationEngine.generate_recommendation(
            dominant_crime_type="theft",
            peak_time="morning",
            risk_level="Low",
            repeat_offenders_count=0,
            known_gangs_count=0,
            crime_count=2,
            hotspot_trend="Stable",
        )
        self.assertIn("theft", rec.lower())
        self.assertIn("morning", rec)
        self.assertNotIn("repeat offenders", rec)
        self.assertNotIn("patrol vehicle", rec)

    # ─────────────────────────────────────────────────────────
    # 2. GEO SERVICE HELPER METHOD TESTS
    # ─────────────────────────────────────────────────────────

    def test_geo_service_calculate_trend_emerging(self):
        service = GeoService(self.db_mock)
        now = datetime.now(timezone.utc)
        # More crimes in the second half of the time span
        timestamps = [
            now - timedelta(days=10), # first half
            now - timedelta(days=1),  # second half
            now - timedelta(days=2),  # second half
            now - timedelta(days=3),  # second half
        ]
        trend = service._calculate_trend(timestamps)
        self.assertEqual(trend, "Emerging")

    def test_geo_service_calculate_trend_declining(self):
        service = GeoService(self.db_mock)
        now = datetime.now(timezone.utc)
        # More crimes in the first half of the time span
        timestamps = [
            now - timedelta(days=10), # first half
            now - timedelta(days=9),  # first half
            now - timedelta(days=8),  # first half
            now - timedelta(days=1),  # second half
        ]
        trend = service._calculate_trend(timestamps)
        self.assertEqual(trend, "Declining")

    def test_geo_service_calculate_trend_stable(self):
        service = GeoService(self.db_mock)
        now = datetime.now(timezone.utc)
        # Equal distribution
        timestamps = [
            now - timedelta(days=10), # first half
            now - timedelta(days=1),  # second half
        ]
        # Less than 3 points defaults to Stable
        trend = service._calculate_trend(timestamps)
        self.assertEqual(trend, "Stable")

    def test_suggested_patrol_window_evening(self):
        service = GeoService(self.db_mock)
        window = service._get_suggested_patrol_window("evening")
        self.assertEqual(window, "17:30-22:30")
        
        window_unknown = service._get_suggested_patrol_window("unknown_slot")
        self.assertEqual(window_unknown, "24-hour dynamic patrols recommended")

    # ─────────────────────────────────────────────────────────
    # 3. ROUTER API TESTS
    # ─────────────────────────────────────────────────────────

    @patch("app.api.v1.routers.geo.GeoService", autospec=True)
    def test_get_hotspots_endpoint(self, mock_service_class):
        # Mock service instance and get_hotspots method
        mock_service_instance = mock_service_class.return_value
        mock_service_instance.get_hotspots = AsyncMock(return_value=[
            HotspotResponse(
                cluster_id=0,
                center_latitude=12.93,
                center_longitude=77.65,
                radius_meters=200.0,
                crime_count=5,
                dominant_crime_type="burglary",
                peak_time="evening",
                suggested_patrol_window="17:30-22:30",
                hotspot_trend="Stable",
                confidence_score=0.5,
                risk_level="Medium",
                repeat_offenders_count=1,
                known_gangs_count=0,
                recommendation="Patrol recommended."
            )
        ])

        response = client.get("/api/v1/geo/hotspots?eps=1000&min_samples=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["cluster_id"], 0)
        self.assertEqual(data[0]["dominant_crime_type"], "burglary")
        self.assertEqual(data[0]["suggested_patrol_window"], "17:30-22:30")
        self.assertEqual(data[0]["hotspot_trend"], "Stable")
        self.assertEqual(data[0]["risk_level"], "Medium")

    @patch("app.api.v1.routers.geo.GeoService", autospec=True)
    def test_get_hotspots_district_endpoint(self, mock_service_class):
        mock_service_instance = mock_service_class.return_value
        mock_service_instance.get_hotspots = AsyncMock(return_value=[])

        response = client.get("/api/v1/geo/district/Mysuru")
        self.assertEqual(response.status_code, 200)
        mock_service_instance.get_hotspots.assert_called_once_with(
            eps=1000.0,
            min_samples=5,
            district="Mysuru",
            crime_type=None,
            start_date=None,
            end_date=None,
        )

    @patch("app.api.v1.routers.geo.GeoService", autospec=True)
    def test_get_hotspots_crime_type_endpoint(self, mock_service_class):
        mock_service_instance = mock_service_class.return_value
        mock_service_instance.get_hotspots = AsyncMock(return_value=[])

        response = client.get("/api/v1/geo/crime-type/burglary")
        self.assertEqual(response.status_code, 200)
        mock_service_instance.get_hotspots.assert_called_once_with(
            eps=1000.0,
            min_samples=5,
            district=None,
            crime_type="burglary",
            start_date=None,
            end_date=None,
        )

    @patch("app.api.v1.routers.geo.GeoService", autospec=True)
    def test_get_statistics_endpoint(self, mock_service_class):
        mock_service_instance = mock_service_class.return_value
        mock_service_instance.get_statistics = AsyncMock(return_value=GeoStatisticsResponse(
            total_crimes_analyzed=100,
            total_hotspots_detected=3,
            total_clustered_crimes=60,
            total_noise_crimes=40,
            top_hotspot_district="Bengaluru Urban",
            average_hotspot_radius_meters=350.5,
            highest_risk_hotspot_id=1,
        ))

        response = client.get("/api/v1/geo/statistics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_crimes_analyzed"], 100)
        self.assertEqual(data["total_hotspots_detected"], 3)
        self.assertEqual(data["top_hotspot_district"], "Bengaluru Urban")
        self.assertEqual(data["average_hotspot_radius_meters"], 350.5)


if __name__ == "__main__":
    unittest.main()
