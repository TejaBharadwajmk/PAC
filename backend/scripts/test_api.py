"""
PAC Backend — Automated API Mock Tests

Tests all FastAPI router endpoints, request/response validation,
status codes, authentication injection, and error handling.
Uses unittest.mock to mock the database engine/sessions and services.
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
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.crime import Crime, CrimeType, CrimeStatus, CrimeSeverity
from app.models.criminal import Criminal, CrimeCriminal, CrimeRole

# Create FastAPI TestClient
client = TestClient(app)

# Helper mock user
MOCK_USER_ID = uuid4()
MOCK_OFFICER = User(
    id=MOCK_USER_ID,
    badge_number="OFF001",
    full_name="HC Ravi Kumar",
    email="off001@ksp.gov.in",
    district="Bengaluru Urban",
    police_station="Whitefield",
    role=UserRole.OFFICER,
    is_active=True,
)

MOCK_ADMIN = User(
    id=uuid4(),
    badge_number="ADMIN001",
    full_name="System Administrator",
    email="admin@ksp.gov.in",
    district="Bengaluru Urban",
    police_station="Headquarters",
    role=UserRole.ADMIN,
    is_active=True,
)


class TestPACAPI(unittest.TestCase):

    def setUp(self):
        # Setup mocks for get_db_session
        self.db_mock = AsyncMock()
        app.dependency_overrides[get_db_session] = lambda: self.db_mock
        
        # Default mock user is Officer
        app.dependency_overrides[get_current_user] = lambda: MOCK_OFFICER

    def tearDown(self):
        app.dependency_overrides.clear()

    # ─────────────────────────────────────────────────────────
    # 1. HEALTH CHECKS
    # ─────────────────────────────────────────────────────────

    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_api_health_endpoint(self):
        response = client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    # ─────────────────────────────────────────────────────────
    # 2. AUTHENTICATION & PROFILE
    # ─────────────────────────────────────────────────────────

    @patch("app.services.auth_service.AuthService.authenticate")
    def test_login_success(self, mock_auth):
        from app.schemas.auth import TokenResponse
        mock_auth.return_value = TokenResponse(
            access_token="mock-access-token",
            refresh_token="mock-refresh-token",
            expires_in=1800,
        )
        payload = {"badge_number": "OFF001", "password": "Password123"}
        response = client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], "mock-access-token")

    def test_login_validation_failure(self):
        # Empty payload
        response = client.post("/api/v1/auth/login", json={})
        self.assertEqual(response.status_code, 422)

    @patch("app.services.auth_service.AuthService.refresh_access_token")
    def test_refresh_token_success(self, mock_refresh):
        from app.schemas.auth import TokenResponse
        mock_refresh.return_value = TokenResponse(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            expires_in=1800,
        )
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": "valid-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], "new-access-token")

    def test_get_profile_me(self):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["badge_number"], "OFF001")

    @patch("app.services.auth_service.AuthService.register_user")
    def test_register_user_by_admin(self, mock_register):
        # Override current user as Admin
        app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
        
        new_user_uuid = uuid4()
        mock_register.return_value = User(
            id=new_user_uuid,
            badge_number="OFF002",
            full_name="New Officer",
            email="off002@ksp.gov.in",
            district="Mysuru",
            police_station="Chamaraja",
            role=UserRole.OFFICER,
            is_active=True,
        )
        
        payload = {
            "badge_number": "OFF002",
            "full_name": "New Officer",
            "email": "off002@ksp.gov.in",
            "password": "StrongPassword@2024",
            "district": "Mysuru",
            "police_station": "Chamaraja",
            "role": "officer"
        }
        response = client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["badge_number"], "OFF002")

    # ─────────────────────────────────────────────────────────
    # 3. CRIME REGISTRATION & QUERY
    # ─────────────────────────────────────────────────────────

    @patch("app.services.dna_service.DNAService.generate", new_callable=AsyncMock)
    @patch("app.services.crime_service.CrimeService.register_crime")
    def test_register_crime_success(self, mock_reg, mock_dna_gen):
        crime_uuid = uuid4()
        occurred_time = datetime.now(timezone.utc)
        mock_reg.return_value = Crime(
            id=crime_uuid,
            fir_number="FIR/BLR/2024/1001",
            crime_type=CrimeType.ROBBERY,
            severity=CrimeSeverity.HIGH,
            status=CrimeStatus.REGISTERED,
            district="Bengaluru Urban",
            police_station="Shivajinagar",
            occurred_at=occurred_time,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_dna_gen.return_value = None  # background task is a no-op in tests
        
        payload = {
            "fir_number": "FIR/BLR/2024/1001",
            "crime_type": "robbery",
            "severity": "high",
            "district": "Bengaluru Urban",
            "police_station": "Shivajinagar",
            "occurred_at": occurred_time.isoformat(),
            "mo_text": "Two suspects robbed gold chain at knifepoint"
        }
        response = client.post("/api/v1/crimes/", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["fir_number"], "FIR/BLR/2024/1001")

    def test_register_crime_validation_error(self):
        # Invalid coordinate ranges (Karnataka limit)
        payload = {
            "fir_number": "FIR/BLR/2024/1001",
            "crime_type": "robbery",
            "district": "Bengaluru Urban",
            "police_station": "Shivajinagar",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "latitude": 50.0,  # invalid (11.5 - 18.5)
            "longitude": 75.0,
        }
        response = client.post("/api/v1/crimes/", json=payload)
        self.assertEqual(response.status_code, 422)

    @patch("app.services.crime_service.CrimeService.get_crime")
    def test_get_crime_by_id(self, mock_get):
        crime_uuid = uuid4()
        occurred_time = datetime.now(timezone.utc)
        mock_get.return_value = Crime(
            id=crime_uuid,
            fir_number="FIR/MYS/2024/0002",
            crime_type=CrimeType.BURGLARY,
            severity=CrimeSeverity.MEDIUM,
            status=CrimeStatus.UNDER_INVESTIGATION,
            district="Mysuru",
            police_station="Lakshmipuram",
            occurred_at=occurred_time,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        response = client.get(f"/api/v1/crimes/{crime_uuid}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fir_number"], "FIR/MYS/2024/0002")

    @patch("app.services.crime_service.CrimeService.get_crime_by_fir")
    def test_get_crime_by_fir(self, mock_get_fir):
        crime_uuid = uuid4()
        occurred_time = datetime.now(timezone.utc)
        mock_get_fir.return_value = Crime(
            id=crime_uuid,
            fir_number="FIR/MYS/2024/0002",
            crime_type=CrimeType.BURGLARY,
            severity=CrimeSeverity.MEDIUM,
            status=CrimeStatus.UNDER_INVESTIGATION,
            district="Mysuru",
            police_station="Lakshmipuram",
            occurred_at=occurred_time,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        response = client.get("/api/v1/crimes/fir/FIR-MYS-2024-0002")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fir_number"], "FIR/MYS/2024/0002")

    @patch("app.services.crime_service.CrimeService.list_crimes")
    def test_list_crimes_paginated(self, mock_list):
        mock_list.return_value = ([], 0)
        response = client.get("/api/v1/crimes/?page=1&page_size=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 0)
        self.assertEqual(response.json()["page"], 1)

    @patch("app.services.crime_service.CrimeService.delete_crime")
    def test_delete_crime_by_officer_fails(self, mock_delete):
        # Current user is Officer — should get 403 Forbidden for DELETE
        response = client.delete(f"/api/v1/crimes/{uuid4()}")
        self.assertEqual(response.status_code, 403)

    @patch("app.services.crime_service.CrimeService.delete_crime")
    def test_delete_crime_by_admin_success(self, mock_delete):
        # Override user as Admin
        app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
        response = client.delete(f"/api/v1/crimes/{uuid4()}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    # ─────────────────────────────────────────────────────────
    # 4. CRIMINAL PROFILES
    # ─────────────────────────────────────────────────────────

    @patch("app.repositories.criminal_repo.CriminalRepository.create")
    def test_register_criminal_success(self, mock_create):
        crim_uuid = uuid4()
        mock_create.return_value = Criminal(
            id=crim_uuid,
            name="Rajesh Kumar Naik",
            aliases=["Rocky"],
            age=28,
            gender="male",
            district="Bengaluru Urban",
            state="Karnataka",
            is_repeat_offender=True,
            previous_cases_count=3,
            gang_name=None,
            gang_affiliation=False,
            is_wanted=True,
            is_arrested=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        payload = {
            "name": "Rajesh Kumar Naik",
            "aliases": ["Rocky"],
            "age": 28,
            "gender": "male",
            "district": "Bengaluru Urban",
            "is_wanted": True
        }
        response = client.post("/api/v1/criminals/", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Rajesh Kumar Naik")

    @patch("app.repositories.criminal_repo.CriminalRepository.get_with_details")
    def test_get_criminal_profile_by_id(self, mock_get_details):
        crim_uuid = uuid4()
        mock_get_details.return_value = Criminal(
            id=crim_uuid,
            name="Ramesh Naik",
            aliases=["Crow"],
            age=35,
            gender="male",
            district="Dakshina Kannada",
            state="Karnataka",
            is_repeat_offender=True,
            previous_cases_count=5,
            gang_name=None,
            gang_affiliation=False,
            is_wanted=True,
            is_arrested=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            crimes=[],
        )
        
        response = client.get(f"/api/v1/criminals/{crim_uuid}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Ramesh Naik")

    @patch("app.repositories.criminal_repo.CriminalRepository.get_crimes_for_criminal")
    @patch("app.repositories.criminal_repo.CriminalRepository.exists")
    def test_get_criminal_crimes_list(self, mock_exists, mock_get_crimes):
        mock_exists.return_value = True
        
        crime_mock = MagicMock()
        crime_mock.fir_number = "FIR/BLR/2024/0001"
        crime_mock.crime_type = CrimeType.ROBBERY
        crime_mock.district = "Bengaluru Urban"
        crime_mock.severity = CrimeSeverity.HIGH
        crime_mock.status = CrimeStatus.REGISTERED
        crime_mock.occurred_at = datetime.now(timezone.utc)

        link_mock = MagicMock()
        link_mock.crime_id = uuid4()
        link_mock.role = CrimeRole.ACCUSED
        link_mock.is_arrested = False
        link_mock.arrest_date = None
        link_mock.notes = "Spotted on CCTV"
        link_mock.crime = crime_mock

        mock_get_crimes.return_value = [link_mock]
        
        response = client.get(f"/api/v1/criminals/{uuid4()}/crimes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["role"], "accused")


if __name__ == "__main__":
    unittest.main()
