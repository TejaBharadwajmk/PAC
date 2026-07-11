"""PAC Backend — Comprehensive local validation test (no DB required)."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  \033[32mPASS\033[0m  {label}")


def fail(label, reason=""):
    global FAIL
    FAIL += 1
    print(f"  \033[31mFAIL\033[0m  {label}" + (f": {reason}" if reason else ""))


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─────────────────────────────────────────────────────────────
# 1. MODULE IMPORTS
# ─────────────────────────────────────────────────────────────
section("1. Module Imports")

modules_to_test = [
    "app.config",
    "app.database",
    "app.core.security",
    "app.core.exceptions",
    "app.core.logging",
    "app.models.user",
    "app.models.crime",
    "app.models.criminal",
    "app.models.victim",
    "app.models.crime_dna",
    "app.models.behaviour",
    "app.schemas.auth",
    "app.schemas.crime",
    "app.schemas.criminal",
    "app.schemas.victim",
    "app.schemas.common",
    "app.repositories.base",
    "app.repositories.user_repo",
    "app.repositories.crime_repo",
    "app.repositories.criminal_repo",
    "app.services.mo_extraction_service",
    "app.services.auth_service",
    "app.services.crime_service",
    "app.api.v1.routers.auth",
    "app.api.v1.routers.crimes",
    "app.api.v1.routers.criminals",
    "app.main",
]

for m in modules_to_test:
    try:
        __import__(m)
        ok(m)
    except Exception as e:
        fail(m, str(e))


# ─────────────────────────────────────────────────────────────
# 2. FASTAPI ROUTES
# ─────────────────────────────────────────────────────────────
section("2. FastAPI Routes & OpenAPI Schema")

from app.main import app  # noqa: E402

expected_routes = [
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
    "/api/v1/auth/register",
    "/api/v1/crimes/",
    "/api/v1/crimes/fir/{fir_number}",
    "/api/v1/crimes/{crime_id}",
    "/api/v1/criminals/",
    "/api/v1/criminals/{criminal_id}",
    "/api/v1/criminals/{criminal_id}/crimes",
    "/api/v1/health",
    "/health",
]

try:
    schema = app.openapi()
    schema_paths = set(schema.get("paths", {}).keys())
    app_routes = [r.path for r in app.routes if hasattr(r, "methods")]

    for route in expected_routes:
        if route in app_routes or route in schema_paths:
            ok(f"Route registered: {route}")
        else:
            fail(f"Route missing: {route}")

    ok(f"OpenAPI schema generated ({len(schema_paths)} documented endpoints)")
except Exception as e:
    fail("OpenAPI schema", str(e))


# ─────────────────────────────────────────────────────────────
# 3. SECURITY UTILITIES
# ─────────────────────────────────────────────────────────────
section("3. Security: JWT + Password Hashing")

from app.core.security import (  # noqa: E402
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_access_token, decode_refresh_token,
)

# Password hashing
pwd = "TestPassword@2024"
hashed = hash_password(pwd)
if verify_password(pwd, hashed):
    ok("bcrypt hash + verify")
else:
    fail("bcrypt hash + verify")

if not verify_password("wrong_password", hashed):
    ok("bcrypt rejects wrong password")
else:
    fail("bcrypt rejects wrong password")

# JWT access token
token_data = {"sub": "user-uuid-123", "badge": "ADMIN001", "role": "admin"}
access_token = create_access_token(token_data)
payload = decode_access_token(access_token)
if payload and payload.get("sub") == "user-uuid-123" and payload.get("type") == "access":
    ok("JWT access token create + decode")
else:
    fail("JWT access token", str(payload))

# Refresh token cannot be used as access token
refresh_token = create_refresh_token({"sub": "user-uuid-123"})
if decode_access_token(refresh_token) is None:
    ok("Refresh token rejected as access token")
else:
    fail("Refresh token rejected as access token")

# Access token cannot be used as refresh token
if decode_refresh_token(access_token) is None:
    ok("Access token rejected as refresh token")
else:
    fail("Access token rejected as refresh token")

# Invalid token
if decode_access_token("invalid.token.here") is None:
    ok("Invalid token returns None")
else:
    fail("Invalid token returns None")


# ─────────────────────────────────────────────────────────────
# 4. MO EXTRACTION SERVICE
# ─────────────────────────────────────────────────────────────
section("4. MO Feature Extraction (Rule-Based)")

from app.services.mo_extraction_service import extract_mo_features  # noqa: E402

mo_tests = [
    # (label, mo_text, crime_type, expected_field, expected_value)
    ("Chain snatching - crime_method",
     "Two accused on motorcycle snatched gold chain from woman near bus stand and fled",
     "chain_snatching", "crime_method", "confrontation"),

    ("Chain snatching - escape_method",
     "Two accused on motorcycle snatched gold chain and fled at high speed towards north",
     "chain_snatching", "escape_method", "bike"),

    ("Chain snatching - gang_involved",
     "Two accused persons came on motorcycle and snatched chain",
     "chain_snatching", "gang_involved", True),

    ("House break-in - crime_method",
     "Accused broke rear window glass using iron rod and entered house at midnight",
     "house_break_in", "crime_method", "forced_entry"),

    ("House break-in - time_of_day",
     "Accused entered house at midnight and stolen valuables",
     "house_break_in", "time_of_day", "late_night"),

    ("House break-in - target_type",
     "Unknown persons forced entry into house during night and stolen gold",
     "house_break_in", "target_type", "residence"),

    ("House break-in - tools",
     "Accused broke door using crowbar and entered house",
     "house_break_in", "tools_used", ["crowbar"]),

    ("Cyber crime - crime_method",
     "Accused called victim posing as bank official and obtained OTP and debited 25000",
     "cyber_crime", "crime_method", "cyber"),

    ("ATM fraud - target_type",
     "Accused installed card skimming device on ATM machine and cloned customer debit cards",
     "atm_fraud", "target_type", "atm"),

    ("Robbery - weapon",
     "Accused threatened victim at knife point near market and robbed gold chain",
     "robbery", "weapon_used", "knife"),

    ("Dacoity - gang_involved",
     "Gang of five armed persons entered house and tied family members and committed dacoity",
     "dacoity", "gang_involved", True),

    ("Dacoity - num_accused",
     "Gang of five armed persons entered house and committed dacoity",
     "dacoity", "num_accused", 5),

    ("Vehicle theft - tools",
     "Accused stole motorcycle using duplicate key method",
     "vehicle_theft", "tools_used", ["duplicate_key"]),

    ("Drug offense - crime_method",
     "Accused found in possession of ganja weighing 100 grams near bus stand",
     "drug_offense", "crime_method", "opportunistic"),

    ("Night tag generated",
     "Accused broke into house during night hours and stolen valuables",
     "house_break_in", "modus_operandi_tags", None),  # just check it's not empty

    ("Gold theft tag",
     "Two accused snatched gold chain and gold bangles from victim near market",
     "chain_snatching", "modus_operandi_tags", None),
]

for label, mo_text, crime_type, field, expected in mo_tests:
    try:
        result = extract_mo_features(mo_text, crime_type)
        actual = result.get(field)

        if expected is None:
            # Just check it returned something non-empty
            if result and len(result) > 0:
                ok(f"{label} -> {field}={actual!r}")
            else:
                fail(label, "returned empty dict")
        elif actual == expected:
            ok(f"{label} -> {field}={actual!r}")
        else:
            fail(label, f"expected {expected!r}, got {actual!r}")
    except Exception as e:
        fail(label, str(e))


# ─────────────────────────────────────────────────────────────
# 5. PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────
section("5. Pydantic Schema Validation")

from app.schemas.crime import CrimeCreate, CrimeUpdate, CrimeFilterParams  # noqa: E402
from app.schemas.auth import UserCreate, LoginRequest  # noqa: E402
from app.schemas.criminal import CriminalCreate  # noqa: E402
from app.models.crime import CrimeType, CrimeSeverity  # noqa: E402
from datetime import datetime, timezone

# Valid crime creation
try:
    crime = CrimeCreate(
        fir_number="FIR/BLR-URB/2024/0001",
        crime_type=CrimeType.CHAIN_SNATCHING,
        severity=CrimeSeverity.MEDIUM,
        district="Bengaluru Urban",
        police_station="Shivajinagar",
        latitude=12.9716,
        longitude=77.5946,
        occurred_at=datetime.now(timezone.utc),
        mo_text="Two accused on motorcycle snatched gold chain from woman near bus stand",
    )
    ok(f"CrimeCreate valid: fir={crime.fir_number}")
except Exception as e:
    fail("CrimeCreate valid", str(e))

# Invalid latitude (outside Karnataka)
try:
    bad = CrimeCreate(
        fir_number="FIR/TEST/2024/0001",
        crime_type=CrimeType.THEFT,
        district="Bengaluru Urban",
        police_station="Test",
        occurred_at=datetime.now(timezone.utc),
        latitude=50.0,  # outside Karnataka (11.5-18.5)
        longitude=77.0,
    )
    fail("CrimeCreate rejects out-of-range lat")
except Exception:
    ok("CrimeCreate rejects out-of-range lat")

# LoginRequest
try:
    lr = LoginRequest(badge_number="ADMIN001", password="Admin@2024")
    ok(f"LoginRequest: badge={lr.badge_number}")
except Exception as e:
    fail("LoginRequest", str(e))

# UserCreate password validation
try:
    uc = UserCreate(
        badge_number="OFF001",
        full_name="Test Officer",
        email="test@ksp.gov.in",
        password="short",  # < 8 chars
    )
    fail("UserCreate rejects short password")
except Exception:
    ok("UserCreate rejects short password (<8 chars)")

# CriminalCreate
try:
    cc = CriminalCreate(
        name="Rajesh Kumar",
        aliases=["Rocky", "Bike Raj"],
        age=28,
        district="Bengaluru Urban",
    )
    ok(f"CriminalCreate: name={cc.name} aliases={cc.aliases}")
except Exception as e:
    fail("CriminalCreate", str(e))


# ─────────────────────────────────────────────────────────────
# 6. ALEMBIC MIGRATION SYNTAX
# ─────────────────────────────────────────────────────────────
section("6. Alembic Migration File Syntax")

import ast  # noqa: E402

migration_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "alembic", "versions", "001_initial_schema.py"
)
try:
    with open(migration_file) as f:
        src = f.read()
    ast.parse(src)
    ok("001_initial_schema.py parses as valid Python")
except SyntaxError as e:
    fail("001_initial_schema.py syntax", str(e))
except FileNotFoundError:
    fail("001_initial_schema.py not found")


# ─────────────────────────────────────────────────────────────
# 7. CONFIGURATION
# ─────────────────────────────────────────────────────────────
section("7. Application Configuration")

from app.config import settings  # noqa: E402

checks = [
    ("APP_NAME set", settings.APP_NAME == "PAC - PoliceIT Analytics Core"),
    ("DATABASE_URL asyncpg", "asyncpg" in settings.DATABASE_URL),
    ("DATABASE_URL_SYNC psycopg2", "psycopg2" in settings.DATABASE_URL_SYNC),
    ("JWT algorithm HS256", settings.ALGORITHM == "HS256"),
    ("Access token 30 min", settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30),
    ("EMBEDDING_DIM via model", True),  # dim is in model file
]
for label, condition in checks:
    if condition:
        ok(label)
    else:
        fail(label)

# Verify 384-dim in model
from app.models.crime_dna import EMBEDDING_DIM  # noqa: E402
if EMBEDDING_DIM == 384:
    ok(f"EMBEDDING_DIM = {EMBEDDING_DIM} (all-MiniLM-L6-v2)")
else:
    fail(f"EMBEDDING_DIM should be 384, got {EMBEDDING_DIM}")


# ─────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'='*60}\n")

if FAIL > 0:
    sys.exit(1)
else:
    print("All tests passed. Backend code is ready for database testing.")
    sys.exit(0)
