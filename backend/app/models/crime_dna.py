"""
PAC — CrimeDNA Model (Phase 2 — Hybrid Intelligence Hub)

crime_dna is a DENORMALISED READ-MODEL. It aggregates intelligence from:
  - crimes (crime_type, district, location, occurred_at)
  - crime_mo (structured MO features)
  - ML Engine (384-dim semantic embedding)

Design rationale (ADR-002):
  - Zero-join similarity queries (all fields in one table)
  - Precomputed time intelligence (no runtime derivation)
  - Status lifecycle (PENDING → PROCESSING → COMPLETED/FAILED)
  - Central hub for Phases 3–4 (Geo, Neo4j, Behaviour, Risk)
"""

import uuid
import enum
from sqlalchemy import (
    Column, Text, String, Boolean, Integer, Float,
    DateTime, ForeignKey, Enum as SAEnum, func, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base

# Embedding dimension — must match all-MiniLM-L6-v2 output
EMBEDDING_DIM: int = 384


class DNAStatus(str, enum.Enum):
    """
    Lifecycle states for the Crime DNA generation pipeline.

    State machine:
      PENDING    → crime registered, awaiting ML Engine processing
      PROCESSING → background task is running (ML Engine called)
      COMPLETED  → embedding stored, ready for similarity search
      FAILED     → generation failed after max retries (retryable via API)
    """
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class CrimeDNA(Base):
    """
    Crime DNA — the behavioural fingerprint of a crime.

    Acts as the central intelligence hub for all PAC analytical modules.
    Populated in stages:
      1. PENDING row created at crime registration (instant)
      2. Background task fills embedding + intelligence fields
      3. COMPLETED → available for similarity search, geo clustering, graph enrichment

    ADR-002: Denormalised read-model pattern.
    Fields are copied from crimes + crime_mo at generation time to enable
    zero-join similarity queries and feature scoring.
    """
    __tablename__ = "crime_dna"

    # ── Primary Key ────────────────────────────────────────
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crime_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crimes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Intelligence Status ────────────────────────────────
    # Tracks the full DNA generation lifecycle
    status = Column(
        SAEnum(
            DNAStatus,
            name="dna_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=DNAStatus.PENDING,
        index=True,
    )
    status_message = Column(Text, nullable=True)          # Error detail on FAILED
    retry_count    = Column(Integer, default=0, nullable=False)

    # ── Semantic Intelligence (filled on COMPLETED) ────────
    # NULL until background task successfully runs
    embedding        = Column(Vector(EMBEDDING_DIM), nullable=True)
    mo_text_embedded = Column(Text, nullable=True)        # Text passed to model
    model_name       = Column(String(100), default="all-MiniLM-L6-v2", nullable=False)
    model_version    = Column(String(50),  default="v1.0")

    # ── Structured MO Intelligence ─────────────────────────
    # Denormalised from crime_mo at generation time.
    # These enable Phase 2 feature scoring + Phase 4 behaviour profiling
    # without any joins.
    crime_type          = Column(String(50),  nullable=True)   # from crimes.crime_type
    crime_method        = Column(String(100), nullable=True)   # from crime_mo
    target_type         = Column(String(100), nullable=True)
    weapon_used         = Column(String(100), nullable=True)
    tools_used          = Column(JSONB, default=list)
    planning_level      = Column(String(50),  nullable=True)
    gang_involved       = Column(Boolean, default=False)
    escape_method       = Column(String(100), nullable=True)
    modus_operandi_tags = Column(JSONB, default=list)

    # ── Time Intelligence ──────────────────────────────────
    # Precomputed from crimes.occurred_at at generation time.
    # Avoids per-query derivation during feature scoring (Phase 2)
    # and is used as XGBoost features directly (Phase 4).
    hour_of_day     = Column(Integer, nullable=True)   # 0–23
    day_of_week     = Column(Integer, nullable=True)   # 0=Monday … 6=Sunday
    is_weekend      = Column(Boolean, nullable=True)   # Saturday or Sunday
    is_night        = Column(Boolean, nullable=True)   # 21:00–05:59
    time_of_day_slot = Column(String(20), nullable=True)  # morning/afternoon/evening/night/late_night
    month           = Column(Integer, nullable=True)   # 1–12 (for seasonal patterns)

    # ── Location Intelligence ──────────────────────────────
    # Denormalised for zero-join geo queries (Phase 3 DBSCAN)
    # and Neo4j node enrichment (Phase 3 Graph).
    district       = Column(String(100), nullable=True)
    police_station = Column(String(200), nullable=True)
    latitude       = Column(Float, nullable=True)
    longitude      = Column(Float, nullable=True)

    # ── Processing Timestamps ──────────────────────────────
    generated_at          = Column(DateTime(timezone=True), nullable=True)  # COMPLETED time
    processing_started_at = Column(DateTime(timezone=True), nullable=True)  # PROCESSING start
    processing_failed_at  = Column(DateTime(timezone=True), nullable=True)  # Last FAILED time

    # ── Record Timestamps ──────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationship ───────────────────────────────────────
    crime = relationship("Crime", back_populates="crime_dna")

    __table_args__ = (
        # Fast lookup of pending/failed records for startup sweep
        Index("ix_crime_dna_status", "status"),
        # District + status for geo-filtered similarity
        Index("ix_crime_dna_district_status", "district", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CrimeDNA crime={self.crime_id!r} "
            f"status={self.status!r} "
            f"model={self.model_name!r}>"
        )
