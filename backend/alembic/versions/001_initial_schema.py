"""Initial schema — all PAC tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00

Creates:
  - Extensions: vector, postgis, uuid-ossp
  - Enum types: user_role, crime_type, crime_severity, crime_status, crime_role
  - Tables: users, crimes, crime_mo, criminals, crime_criminals,
            victims, crime_victims, crime_dna, behaviour_profiles
  - Indexes: composite, spatial (PostGIS), vector (IVFFlat cosine)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── Enum Types ─────────────────────────────────────────
    op.execute("CREATE TYPE user_role AS ENUM ('officer','analyst','supervisor','admin')")
    op.execute(
        "CREATE TYPE crime_type AS ENUM ("
        "'murder','robbery','burglary','theft','chain_snatching','vehicle_theft',"
        "'house_break_in','auto_theft','cyber_crime','atm_fraud','assault','kidnapping',"
        "'fraud','dacoity','extortion','drug_offense','sexual_assault','other')"
    )
    op.execute("CREATE TYPE crime_severity AS ENUM ('low','medium','high','critical')")
    op.execute("CREATE TYPE crime_status AS ENUM ('registered','under_investigation','chargesheeted','solved','closed')")
    op.execute("CREATE TYPE crime_role AS ENUM ('accused','suspect','witness')")

    # ── users ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE users (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            badge_number    VARCHAR(50)  NOT NULL UNIQUE,
            full_name       VARCHAR(200) NOT NULL,
            email           VARCHAR(255) NOT NULL UNIQUE,
            district        VARCHAR(100),
            police_station  VARCHAR(200),
            role            user_role    NOT NULL DEFAULT 'officer',
            hashed_password VARCHAR(255) NOT NULL,
            is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
            last_login      TIMESTAMPTZ,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_users_badge_number ON users(badge_number)")
    op.execute("CREATE INDEX ix_users_email ON users(email)")
    op.execute("CREATE INDEX ix_users_district ON users(district)")

    # ── crimes ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE crimes (
            id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            fir_number       VARCHAR(100)   NOT NULL UNIQUE,
            crime_type       crime_type     NOT NULL,
            severity         crime_severity NOT NULL DEFAULT 'medium',
            status           crime_status   NOT NULL DEFAULT 'registered',
            district         VARCHAR(100)   NOT NULL,
            police_station   VARCHAR(200)   NOT NULL,
            location_address VARCHAR(500),
            latitude         DOUBLE PRECISION,
            longitude        DOUBLE PRECISION,
            geom             GEOMETRY(POINT, 4326),
            description      TEXT,
            mo_text          TEXT,
            occurred_at      TIMESTAMPTZ    NOT NULL,
            reported_at      TIMESTAMPTZ    DEFAULT NOW(),
            registered_by    UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_crimes_fir_number ON crimes(fir_number)")
    op.execute("CREATE INDEX ix_crimes_crime_type ON crimes(crime_type)")
    op.execute("CREATE INDEX ix_crimes_status ON crimes(status)")
    op.execute("CREATE INDEX ix_crimes_district ON crimes(district)")
    op.execute("CREATE INDEX ix_crimes_occurred_at ON crimes(occurred_at)")
    op.execute("CREATE INDEX ix_crimes_district_type ON crimes(district, crime_type)")
    op.execute("CREATE INDEX ix_crimes_occurred_district ON crimes(occurred_at, district)")
    op.execute("CREATE INDEX ix_crimes_geom ON crimes USING GIST(geom)")

    # ── crime_mo (MO features — one-to-one with crime) ────
    op.execute("""
        CREATE TABLE crime_mo (
            id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            crime_id             UUID NOT NULL UNIQUE REFERENCES crimes(id) ON DELETE CASCADE,
            crime_method         VARCHAR(100),
            entry_method         VARCHAR(100),
            target_type          VARCHAR(100),
            weapon_used          VARCHAR(100),
            tools_used           JSONB DEFAULT '[]',
            time_of_day          VARCHAR(50),
            day_type             VARCHAR(50),
            planning_level       VARCHAR(50),
            gang_involved        BOOLEAN DEFAULT FALSE,
            num_accused          INTEGER DEFAULT 1,
            escape_method        VARCHAR(100),
            vehicle_used_in_crime BOOLEAN DEFAULT FALSE,
            modus_operandi_tags  JSONB DEFAULT '[]',
            extraction_method    VARCHAR(50) DEFAULT 'rule_based',
            extracted_at         TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_crime_mo_crime_id ON crime_mo(crime_id)")

    # ── criminals ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE criminals (
            id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name                 VARCHAR(200) NOT NULL,
            aliases              JSONB DEFAULT '[]',
            date_of_birth        DATE,
            age                  INTEGER,
            gender               VARCHAR(20) DEFAULT 'male',
            district             VARCHAR(100),
            state                VARCHAR(100) DEFAULT 'Karnataka',
            address              TEXT,
            contact_number       VARCHAR(20),
            aadhaar_last4        VARCHAR(4),
            is_repeat_offender   BOOLEAN DEFAULT FALSE,
            previous_cases_count INTEGER DEFAULT 0,
            gang_name            VARCHAR(200),
            gang_affiliation     BOOLEAN DEFAULT FALSE,
            height_cm            INTEGER,
            build                VARCHAR(50),
            identifying_marks    TEXT,
            is_wanted            BOOLEAN DEFAULT FALSE,
            is_arrested          BOOLEAN DEFAULT FALSE,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_criminals_name ON criminals(name)")
    op.execute("CREATE INDEX ix_criminals_district ON criminals(district)")
    op.execute("CREATE INDEX ix_criminals_is_repeat ON criminals(is_repeat_offender)")
    op.execute("CREATE INDEX ix_criminals_is_wanted ON criminals(is_wanted)")
    op.execute("CREATE INDEX ix_criminals_gang_name ON criminals(gang_name)")

    # ── crime_criminals (many-to-many) ────────────────────
    op.execute("""
        CREATE TABLE crime_criminals (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            crime_id    UUID NOT NULL REFERENCES crimes(id) ON DELETE CASCADE,
            criminal_id UUID NOT NULL REFERENCES criminals(id) ON DELETE CASCADE,
            role        crime_role DEFAULT 'accused',
            is_arrested BOOLEAN DEFAULT FALSE,
            arrest_date TIMESTAMPTZ,
            notes       TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_crime_criminal UNIQUE (crime_id, criminal_id)
        )
    """)
    op.execute("CREATE INDEX ix_crime_criminals_crime_id ON crime_criminals(crime_id)")
    op.execute("CREATE INDEX ix_crime_criminals_criminal_id ON crime_criminals(criminal_id)")

    # ── victims ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE victims (
            id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name           VARCHAR(200) NOT NULL,
            age            INTEGER,
            gender         VARCHAR(20),
            occupation     VARCHAR(200),
            district       VARCHAR(100),
            address        TEXT,
            contact_number VARCHAR(20),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_victims_name ON victims(name)")
    op.execute("CREATE INDEX ix_victims_district ON victims(district)")

    # ── crime_victims (many-to-many) ──────────────────────
    op.execute("""
        CREATE TABLE crime_victims (
            id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            crime_id         UUID NOT NULL REFERENCES crimes(id) ON DELETE CASCADE,
            victim_id        UUID NOT NULL REFERENCES victims(id) ON DELETE CASCADE,
            injury_type      VARCHAR(50) DEFAULT 'none',
            loss_amount      NUMERIC(15,2),
            loss_description TEXT,
            created_at       TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_crime_victim UNIQUE (crime_id, victim_id)
        )
    """)
    op.execute("CREATE INDEX ix_crime_victims_crime_id ON crime_victims(crime_id)")
    op.execute("CREATE INDEX ix_crime_victims_victim_id ON crime_victims(victim_id)")

    # ── crime_dna (384-dim Crime DNA vectors) ─────────────
    op.execute("""
        CREATE TABLE crime_dna (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            crime_id        UUID NOT NULL UNIQUE REFERENCES crimes(id) ON DELETE CASCADE,
            embedding       vector(384) NOT NULL,
            mo_text_embedded TEXT,
            model_name      VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
            model_version   VARCHAR(50) DEFAULT 'v1.0',
            generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_crime_dna_crime_id ON crime_dna(crime_id)")
    # IVFFlat index for approximate nearest-neighbour cosine search
    # lists=100 is appropriate for ~10k-100k vectors; tune after data load
    op.execute(
        "CREATE INDEX ix_crime_dna_embedding "
        "ON crime_dna USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # ── behaviour_profiles ────────────────────────────────
    op.execute("""
        CREATE TABLE behaviour_profiles (
            id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            criminal_id          UUID NOT NULL UNIQUE REFERENCES criminals(id) ON DELETE CASCADE,
            preferred_crime_types JSONB DEFAULT '[]',
            preferred_districts  JSONB DEFAULT '[]',
            preferred_time_of_day VARCHAR(50),
            preferred_target_type VARCHAR(100),
            planning_level       VARCHAR(50),
            escape_pattern       VARCHAR(100),
            avg_gang_size        DOUBLE PRECISION,
            operating_radius_km  DOUBLE PRECISION,
            crime_frequency_days DOUBLE PRECISION,
            risk_score           DOUBLE PRECISION DEFAULT 0.0,
            risk_level           VARCHAR(20) DEFAULT 'low',
            profile_summary      TEXT,
            generated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_updated         TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_behaviour_profiles_criminal_id ON behaviour_profiles(criminal_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS behaviour_profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS crime_dna CASCADE")
    op.execute("DROP TABLE IF EXISTS crime_victims CASCADE")
    op.execute("DROP TABLE IF EXISTS victims CASCADE")
    op.execute("DROP TABLE IF EXISTS crime_criminals CASCADE")
    op.execute("DROP TABLE IF EXISTS criminals CASCADE")
    op.execute("DROP TABLE IF EXISTS crime_mo CASCADE")
    op.execute("DROP TABLE IF EXISTS crimes CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TYPE IF EXISTS crime_role")
    op.execute("DROP TYPE IF EXISTS crime_status")
    op.execute("DROP TYPE IF EXISTS crime_severity")
    op.execute("DROP TYPE IF EXISTS crime_type")
    op.execute("DROP TYPE IF EXISTS user_role")
