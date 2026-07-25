"""
PAC — CCTNS Data Ingestion & Staging Models

SQLAlchemy ORM models for tracking CCTNS ETL import logs
and raw staging transaction payloads.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, Enum as SQLEnum, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CCTNSSyncStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class CCTNSImportLog(Base):
    """Audit log of CCTNS ETL sync runs."""

    __tablename__ = "cctns_import_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    records_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[CCTNSSyncStatus] = mapped_column(
        SQLEnum(CCTNSSyncStatus, name="cctns_sync_status"),
        default=CCTNSSyncStatus.RUNNING,
        nullable=False,
    )
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CCTNSRawStaging(Base):
    """Raw CCTNS transaction staging table for legacy FIR ingest payloads."""

    __tablename__ = "cctns_raw_staging"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cctns_fir_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    is_processed: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
