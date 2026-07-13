"""
PAC Backend — Criminal Network Intelligence (Neo4j) Unit Tests
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
from app.services.graph_service import GraphService
from app.repositories.graph_repo import GraphRepository

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


class TestCriminalNetworkIntelligence(unittest.TestCase):

    def setUp(self):
        self.db_mock = AsyncMock()
        self.neo4j_session_mock = AsyncMock()

        app.dependency_overrides[get_db_session] = lambda: self.db_mock
        app.dependency_overrides[get_neo4j_session] = lambda: self.neo4j_session_mock
        app.dependency_overrides[get_current_user] = lambda: MOCK_OFFICER

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.repositories.graph_repo.GraphRepository.sync_crime_nodes_batch")
    @patch("app.repositories.graph_repo.GraphRepository.sync_crime_criminals_batch")
    def test_sync_crime_node(self, mock_criminals, mock_crime_nodes):
        # Setup mock crime
        crime_id = uuid4()
        mock_crime = MagicMock()
        mock_crime.id = crime_id
        mock_crime.fir_number = "FIR/001"
        mock_crime.crime_type.value = "burglary"
        mock_crime.severity.value = "major"
        mock_crime.occurred_at = datetime.now(timezone.utc)
        mock_crime.crime_dna = None
        mock_crime.district = "Bengaluru Urban"
        mock_crime.police_station = "Koramangala"
        mock_crime.victims = []

        # DB execute mock setup
        db_res_mock = MagicMock()
        db_res_mock.scalar_one_or_none.return_value = mock_crime
        db_res_mock.scalars.return_value.all.return_value = []
        self.db_mock.execute.return_value = db_res_mock

        # Run sync request
        response = client.post("/api/v1/graph/sync", json={"crime_ids": [str(crime_id)]})
        self.assertEqual(response.status_code, 200)
        
        json_data = response.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["synchronized_count"], 1)
        
        # Verify repo layer called
        mock_crime_nodes.assert_called_once()

    @patch("app.repositories.graph_repo.GraphRepository.sync_criminal_nodes_batch")
    def test_sync_criminal_node(self, mock_criminal_nodes):
        criminal_id = uuid4()
        mock_criminal = MagicMock()
        mock_criminal.id = criminal_id
        mock_criminal.name = "John Doe"
        mock_criminal.is_repeat_offender = True
        mock_criminal.aliases = ["JD", "Johnny"]
        mock_criminal.district = "Bengaluru Urban"
        mock_criminal.gang_name = "Koramangala Boys"
        mock_criminal.behaviour_profile = None

        db_res_mock = MagicMock()
        db_res_mock.scalar_one_or_none.return_value = mock_criminal
        db_res_mock.scalars.return_value.all.return_value = []
        self.db_mock.execute.return_value = db_res_mock

        response = client.post("/api/v1/graph/sync", json={"criminal_ids": [str(criminal_id)]})
        self.assertEqual(response.status_code, 200)
        
        json_data = response.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["synchronized_count"], 1)
        
        mock_criminal_nodes.assert_called_once()

    @patch("app.repositories.graph_repo.GraphRepository.get_node_by_label_and_id")
    def test_get_crime_node_not_found(self, mock_get_node):
        mock_get_node.return_value = None
        crime_id = uuid4()
        response = client.get(f"/api/v1/graph/crime/{crime_id}")
        self.assertEqual(response.status_code, 404)

    @patch("app.repositories.graph_repo.GraphRepository.get_node_by_label_and_id")
    def test_get_crime_node_success(self, mock_get_node):
        crime_id = uuid4()
        mock_get_node.return_value = {
            "id": str(crime_id),
            "label": "Crime",
            "properties": {"fir_number": "FIR/23"}
        }
        response = client.get(f"/api/v1/graph/crime/{crime_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["properties"]["fir_number"], "FIR/23")

    @patch("app.repositories.graph_repo.GraphRepository.get_criminal_network")
    def test_get_criminal_network(self, mock_get_network):
        criminal_id = uuid4()
        mock_get_network.return_value = (
            [{"id": str(criminal_id), "label": "Criminal", "properties": {"name": "Test"}}],
            []
        )
        response = client.get(f"/api/v1/graph/network/{criminal_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["nodes"]), 1)

    @patch("app.repositories.graph_repo.GraphRepository.get_shortest_path")
    def test_get_shortest_path(self, mock_get_path):
        c1 = uuid4()
        c2 = uuid4()
        mock_get_path.return_value = (
            [{"id": str(c1), "label": "Criminal", "properties": {}}],
            [],
            0
        )
        response = client.get(f"/api/v1/graph/shortest-path/{c1}/{c2}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["found"])
        self.assertEqual(response.json()["distance"], 0)

    @patch("app.repositories.graph_repo.GraphRepository.get_graph_statistics")
    def test_get_statistics(self, mock_get_stats):
        mock_get_stats.return_value = {
            "node_counts": {"Criminal": 5, "Crime": 10},
            "relationship_counts": {"CRIMINAL_COMMITTED_CRIME": 8}
        }
        response = client.get("/api/v1/graph/statistics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["node_counts"]["Criminal"], 5)
        self.assertEqual(response.json()["relationship_counts"]["CRIMINAL_COMMITTED_CRIME"], 8)


if __name__ == "__main__":
    unittest.main()
