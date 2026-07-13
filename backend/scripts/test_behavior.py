"""
PAC Backend — Criminal Behaviour Intelligence (Phase 3.3) Unit Tests
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from fastapi.testclient import TestClient

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db_session
from app.graph_db import get_neo4j_session
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.crime import Crime, CrimeType, CrimeSeverity
from app.models.criminal import Criminal
from app.models.crime_dna import CrimeDNA
from app.models.behaviour import BehaviourProfile
from app.services.behavior_engine import BehaviorEngine, haversine_distance

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


class TestCriminalBehaviourIntelligence(unittest.TestCase):

    def setUp(self):
        self.db_mock = AsyncMock()
        self.neo4j_session_mock = AsyncMock()

        app.dependency_overrides[get_db_session] = lambda: self.db_mock
        app.dependency_overrides[get_neo4j_session] = lambda: self.neo4j_session_mock
        app.dependency_overrides[get_current_user] = lambda: MOCK_OFFICER

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_haversine_distance(self):
        # Distance between Bangalore and Mysore (approx 135 km)
        bangalore = (12.9716, 77.5946)
        mysore = (12.2958, 76.6394)
        dist = haversine_distance(bangalore[0], bangalore[1], mysore[0], mysore[1])
        self.assertTrue(120.0 < dist < 150.0)

        # Distance with None values
        self.assertEqual(haversine_distance(None, 77.5946, 12.9716, None), 0.0)

    def test_behavior_engine_empty_history(self):
        criminal = Criminal(id=uuid4(), name="Alpha Criminal", gang_affiliation=False)
        analysis = BehaviorEngine.analyze(criminal, [], [], {})
        self.assertEqual(analysis["scores"]["risk_score"], 0.0)
        self.assertEqual(analysis["scores"]["risk_level"], "LOW")
        self.assertIn("No crime history", analysis["summary"])

    def test_behavior_engine_analysis(self):
        criminal = Criminal(id=uuid4(), name="Alpha Criminal", gang_affiliation=True, gang_name="Alpha Crew", previous_cases_count=5)
        
        crime1 = MagicMock(spec=Crime)
        crime1.id = uuid4()
        crime1.crime_type = CrimeType.BURGLARY
        crime1.severity = CrimeSeverity.HIGH
        crime1.occurred_at = datetime(2026, 7, 10, 22, 0, 0, tzinfo=timezone.utc)
        crime1.district = "Bengaluru Urban"
        crime1.police_station = "Koramangala"
        crime1.latitude = 12.9352
        crime1.longitude = 77.6245

        crime2 = MagicMock(spec=Crime)
        crime2.id = uuid4()
        crime2.crime_type = CrimeType.BURGLARY
        crime2.severity = CrimeSeverity.CRITICAL
        crime2.occurred_at = datetime(2026, 7, 11, 23, 0, 0, tzinfo=timezone.utc)
        crime2.district = "Bengaluru Urban"
        crime2.police_station = "Koramangala"
        crime2.latitude = 12.9301
        crime2.longitude = 77.6201

        dna1 = MagicMock(spec=CrimeDNA)
        dna1.crime_id = crime1.id
        dna1.escape_method = "bike"
        dna1.target_type = "residential"
        dna1.planning_level = "planned"
        dna1.modus_operandi_tags = ["lock_breaking", "night_operation"]
        dna1.weapon_used = "crowbar"

        dna2 = MagicMock(spec=CrimeDNA)
        dna2.crime_id = crime2.id
        dna2.escape_method = "bike"
        dna2.target_type = "residential"
        dna2.planning_level = "planned"
        dna2.modus_operandi_tags = ["lock_breaking", "night_operation"]
        dna2.weapon_used = "crowbar"

        network_metrics = {
            "co_offender_count": 2,
            "strongest_associate": "Beta Criminal",
            "association_strength": 2.0,
            "gang_name": "Alpha Crew"
        }

        results = BehaviorEngine.analyze(criminal, [crime1, crime2], [dna1, dna2], network_metrics)
        
        self.assertIn("Alpha Criminal", criminal.name)
        self.assertEqual(results["scores"]["risk_level"], "HIGH") # high risk due to CRITICAL severity + weapons + gang
        self.assertEqual(results["patterns"]["primary_crime_type"], "burglary")
        self.assertEqual(results["patterns"]["preferred_time_slot"], "night")
        self.assertEqual(results["geo"]["preferred_district"], "Bengaluru Urban")
        self.assertTrue(results["geo"]["operating_radius_km"] > 0.0)
        self.assertIn("detailed_metrics", results)
        self.assertTrue(len(results["evidence"]) >= 4)
        self.assertIn("evidence", results["detailed_metrics"])

    @patch("app.services.behavior_service.BehaviorService.get_or_generate_profile")
    def test_get_behavior_profile_endpoint(self, mock_get_profile):
        criminal_id = uuid4()
        
        mock_profile = MagicMock(spec=BehaviourProfile)
        mock_profile.detailed_metrics = {
            "summary": "High risk serial offender.",
            "scores": {
                "risk_score": 0.85,
                "risk_level": "HIGH",
                "violence_score": 0.5,
                "gang_affiliation_score": 0.3,
                "behaviour_consistency_score": 0.7,
                "serial_offender_probability": 0.6,
                "behaviour_confidence_score": 0.8
            },
            "patterns": {
                "primary_crime_type": "burglary",
                "preferred_time_slot": "night",
                "preferred_day_of_week": "Friday",
                "preferred_season_month": "July",
                "preferred_escape_method": "bike",
                "preferred_target_type": "residential",
                "preferred_planning_level": "planned",
                "modus_operandi_tags": ["lock_breaking"]
            },
            "geo": {
                "operating_radius_km": 4.5,
                "preferred_district": "Bengaluru Urban",
                "preferred_police_station": "Koramangala"
            },
            "evidence": ["Test evidence 1"],
            "recommendations": ["Test recommendation 1"],
            "detailed_metrics": {}
        }
        mock_get_profile.return_value = mock_profile

        response = client.get(f"/api/v1/behavior/criminal/{criminal_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scores"]["risk_level"], "HIGH")
        self.assertEqual(response.json()["evidence"][0], "Test evidence 1")

    @patch("app.repositories.behavior_repo.BehaviorRepository.get_high_risk")
    def test_get_high_risk_endpoint(self, mock_get_high_risk):
        criminal_id = uuid4()
        mock_criminal = MagicMock()
        mock_criminal.name = "John Doe"
        mock_criminal.aliases = ["JD"]

        p_mock = MagicMock()
        p_mock.criminal_id = criminal_id
        p_mock.criminal = mock_criminal
        p_mock.risk_score = 0.95
        p_mock.risk_level = "HIGH"
        p_mock.preferred_modus_operandi = ["burglary"]
        p_mock.last_updated = datetime.now(timezone.utc)
        p_mock.generated_at = datetime.now(timezone.utc)

        mock_get_high_risk.return_value = [p_mock]

        response = client.get("/api/v1/behavior/high-risk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], "John Doe")

    @patch("app.repositories.behavior_repo.BehaviorRepository.get_statistics")
    def test_statistics_endpoint(self, mock_stats):
        mock_stats.return_value = {
            "total_profiles": 10,
            "average_risk_score": 0.45,
            "average_consistency_score": 0.65,
            "average_operating_radius_km": 5.2,
            "risk_level_distribution": {"low": 4, "medium": 4, "high": 2}
        }
        response = client.get("/api/v1/behavior/statistics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_profiles"], 10)
        self.assertEqual(response.json()["risk_level_distribution"]["high"], 2)


if __name__ == "__main__":
    unittest.main()
