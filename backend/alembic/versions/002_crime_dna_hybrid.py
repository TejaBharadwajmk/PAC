"""PAC — Phase 2 Alembic Migration: Hybrid Crime DNA Intelligence Hub

Revision ID: 002
Revises: 001
Create Date: 2026-07-11

Changes:
  - Creates dna_status ENUM type
  - Makes crime_dna.embedding nullable (NULL until COMPLETED)
  - Adds: status, status_message, retry_count (pipeline lifecycle)
  - Adds: processing_started_at, processing_failed_at (timestamps)
  - Adds: crime_type, crime_method, target_type, weapon_used,
          tools_used, planning_level, gang_involved, escape_method,
          modus_operandi_tags (structured MO intelligence)
  - Adds: hour_of_day, day_of_week, is_weekend, is_night,
          time_of_day_slot, month (time intelligence)
  - Adds: district, police_station, latitude, longitude (location intelligence)
  - Adds: created_at, updated_at (record timestamps)
  - Adds composite indexes for status and district+status lookups
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create dna_status ENUM ─────────────────────────
    op.execute(
        "CREATE TYPE dna_status AS ENUM "
        "('pending', 'processing', 'completed', 'failed')"
    )

    # ── 2. Make embedding nullable ─────────────────────────
    # Phase 1 had NOT NULL; Phase 2 creates PENDING rows before embedding
    op.execute(
        "ALTER TABLE crime_dna ALTER COLUMN embedding DROP NOT NULL"
    )

    # ── 3. Status lifecycle columns ───────────────────────
    op.execute(
        "ALTER TABLE crime_dna "
        "ADD COLUMN status          dna_status  NOT NULL DEFAULT 'pending', "
        "ADD COLUMN status_message  TEXT, "
        "ADD COLUMN retry_count     INTEGER     NOT NULL DEFAULT 0"
    )

    # ── 4. Processing timestamps ──────────────────────────
    op.execute(
        "ALTER TABLE crime_dna "
        "ADD COLUMN processing_started_at TIMESTAMPTZ, "
        "ADD COLUMN processing_failed_at  TIMESTAMPTZ"
    )

    # ── 5. Structured MO intelligence ────────────────────
    op.execute(
        "ALTER TABLE crime_dna "
        "ADD COLUMN crime_type          VARCHAR(50), "
        "ADD COLUMN crime_method        VARCHAR(100), "
        "ADD COLUMN target_type         VARCHAR(100), "
        "ADD COLUMN weapon_used         VARCHAR(100), "
        "ADD COLUMN tools_used          JSONB DEFAULT '[]', "
        "ADD COLUMN planning_level      VARCHAR(50), "
        "ADD COLUMN gang_involved       BOOLEAN DEFAULT FALSE, "
        "ADD COLUMN escape_method       VARCHAR(100), "
        "ADD COLUMN modus_operandi_tags JSONB DEFAULT '[]'"
    )

    # ── 6. Time intelligence ──────────────────────────────
    op.execute(
        "ALTER TABLE crime_dna "
        "ADD COLUMN hour_of_day      INTEGER, "
        "ADD COLUMN day_of_week      INTEGER, "
        "ADD COLUMN is_weekend       BOOLEAN, "
        "ADD COLUMN is_night         BOOLEAN, "
        "ADD COLUMN time_of_day_slot VARCHAR(20), "
        "ADD COLUMN month            INTEGER"
    )

    # ── 7. Location intelligence ──────────────────────────
    op.execute(
        "ALTER TABLE crime_dna "
        "ADD COLUMN district        VARCHAR(100), "
        "ADD COLUMN police_station  VARCHAR(200), "
        "ADD COLUMN latitude        DOUBLE PRECISION, "
        "ADD COLUMN longitude       DOUBLE PRECISION"
    )

    # ── 8. Record timestamps ──────────────────────────────
    op.execute(
        "ALTER TABLE crime_dna "
        "ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), "
        "ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    )

    # ── 9. Indexes ────────────────────────────────────────
    op.execute("CREATE INDEX ix_crime_dna_status ON crime_dna(status)")
    op.execute(
        "CREATE INDEX ix_crime_dna_district_status "
        "ON crime_dna(district, status)"
    )

    # ── 10. Backfill existing Phase 1 records ────────────
    # Any existing rows with embeddings should be marked COMPLETED
    op.execute(
        "UPDATE crime_dna SET status = 'completed', "
        "generated_at = NOW(), created_at = NOW(), updated_at = NOW() "
        "WHERE embedding IS NOT NULL"
    )


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_crime_dna_district_status")
    op.execute("DROP INDEX IF EXISTS ix_crime_dna_status")

    # Drop all Phase 2 columns
    cols = [
        "status", "status_message", "retry_count",
        "processing_started_at", "processing_failed_at",
        "crime_type", "crime_method", "target_type", "weapon_used",
        "tools_used", "planning_level", "gang_involved", "escape_method",
        "modus_operandi_tags",
        "hour_of_day", "day_of_week", "is_weekend", "is_night",
        "time_of_day_slot", "month",
        "district", "police_station", "latitude", "longitude",
        "created_at", "updated_at",
    ]
    drop_sql = ", ".join(f"DROP COLUMN IF EXISTS {c}" for c in cols)
    op.execute(f"ALTER TABLE crime_dna {drop_sql}")

    # Restore NOT NULL on embedding
    op.execute(
        "ALTER TABLE crime_dna ALTER COLUMN embedding SET NOT NULL"
    )

    # Drop enum
    op.execute("DROP TYPE IF EXISTS dna_status")
