"""
PAC Backend — Predictive Intelligence (Phase 3.4) Unit Tests
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi.testclient import TestClient

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db_session
from app.graph_db import get_neo4j_session
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.prediction import PredictionProfile
from app.services.prediction_engine import PredictionEngine

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


class TestPredictiveIntelligence(unittest.TestCase):

    def setUp(self):
        self.db_mock = AsyncMock()
        self.neo4j_session_mock = AsyncMock()

        app.dependency_overrides[get_db_session] = lambda: self.db_mock
        app.dependency_overrides[get_neo4j_session] = lambda: self.neo4j_session_mock
        app.dependency_overrides[get_current_user] = lambda: MOCK_OFFICER

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_prediction_engine_criminal_risk(self):
        criminal_data = {
            "previous_cases_count": 3,
            "gang_affiliation": True,
            "gang_name": "Koramangala Boys"
        }
        crimes = [
            {
                "id": str(uuid4()),
                "crime_type": "murder",
                "occurred_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        behaviour_profile = {
            "score_breakdown": {
                "behaviour_consistency_score": 0.8,
                "violence_score": 0.9,
                "gang_affiliation_score": 0.7
            },
            "geo_metrics": {
                "operating_radius_km": 2.5
            },
            "timeline": {
                "escalation_trend": "Emerging"
            }
        }
        network_metrics = {
            "co_offender_count": 3,
            "association_strength": 1.5,
            "gang_name": "Koramangala Boys",
            "hotspots_count": 2
        }

        res = PredictionEngine.calculate_criminal_risk(
            criminal_data=criminal_data,
            crimes=crimes,
            behaviour_profile=behaviour_profile,
            network_metrics=network_metrics
        )

        self.assertIn("risk_score", res)
        self.assertEqual(res["risk_level"], "CRITICAL") # High risk due to murder severity + gang + violent behavior
        self.assertTrue(len(res["evidence"]) >= 3)
        self.assertIn("recommendations", res)

    def test_district_risk_index(self):
        score = PredictionEngine.calculate_district_risk(
            hotspot_count=5,
            crime_volume=120,
            repeat_offender_count=25,
            active_gang_count=3
        )
        self.assertTrue(0.0 <= score <= 100.0)

    def test_hotspot_growth_forecast(self):
        forecast = PredictionEngine.forecast_hotspot_growth(
            recent_velocity=0.8,
            historical_growth=0.7,
            nearby_influence=0.4
        )
        self.assertEqual(forecast, "Growing")

    def test_gang_threat(self):
        threat = PredictionEngine.calculate_gang_threat(
            member_count=15,
            crime_count=45,
            violence_ratio=0.8,
            network_density=0.6
        )
        self.assertEqual(threat, "CRITICAL")

    def test_investigation_priority(self):
        priority = PredictionEngine.calculate_investigation_priority(
            severity_score=0.9,
            behaviour_risk=0.8,
            gang_threat=0.7,
            similar_crime_count=5,
            hotspot_risk=0.6
        )
        self.assertTrue(1.0 <= priority <= 100.0)

    @patch("app.services.prediction_service.PredictionService.get_or_generate_criminal_prediction")
    def test_get_criminal_prediction_endpoint(self, mock_get_pred):
        criminal_id = uuid4()
        mock_pred = MagicMock(spec=PredictionProfile)
        mock_pred.id = uuid4()
        mock_pred.entity_type = "criminal"
        mock_pred.entity_id = str(criminal_id)
        mock_pred.prediction_type = "risk"
        mock_pred.prediction_score = 0.85
        mock_pred.confidence = 0.92
        mock_pred.risk_level = "CRITICAL"
        mock_pred.prediction_reason_code = "SERIAL_PATTERN"
        mock_pred.prediction_version = "1.0"
        mock_pred.generated_at = datetime.now(timezone.utc)
        mock_pred.evidence = ["Factual statement 1"]
        mock_pred.recommendations = ["Rec 1"]
        mock_pred.score_breakdown = {"severity": 0.9}
        mock_pred.detailed_metrics = {}

        mock_get_pred.return_value = mock_pred

        response = client.get(f"/api/v1/predictions/criminal/{criminal_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_level"], "CRITICAL")
        self.assertEqual(response.json()["prediction_reason_code"], "SERIAL_PATTERN")

    @patch("app.repositories.prediction_repo.PredictionRepository.get_statistics")
    def test_statistics_endpoint(self, mock_stats):
        mock_stats.return_value = {
            "total_criminal_predictions": 120,
            "average_criminal_risk_score": 0.54,
            "risk_level_distribution": {
                "low": 30,
                "moderate": 50,
                "high": 30,
                "critical": 10
            }
        }
        response = client.get("/api/v1/predictions/statistics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_criminal_predictions"], 120)
        self.assertEqual(response.json()["risk_level_distribution"]["critical"], 10)


if __name__ == "__main__":
    unittest.main()
