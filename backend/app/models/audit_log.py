"""
PAC — AuditLog Model

Records every significant user action for chain-of-custody compliance.
Captures: who, what, where, when, and response outcome.
"""

import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Integer, Float,
    DateTime, Enum as SAEnum, func, Index,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AuditAction(str, enum.Enum):
    LOGIN    = "login"
    LOGOUT   = "logout"
    SEARCH   = "search"
    VIEW     = "view"
    CREATE   = "create"
    UPDATE   = "update"
    DELETE   = "delete"
    REINDEX  = "reindex"
    AI_QUERY = "ai_query"


class AuditLog(Base):
    """
    Immutable audit record for a single API request.

    Columns
    -------
    user_id      : UUID of the authenticated officer (null for anonymous).
    badge_number : Denormalized badge number for fast human-readable queries
                   without joining the users table.
    action       : Classified action type (see AuditAction enum).
    endpoint     : Request path, e.g. "/api/v1/similarity/search".
    method       : HTTP verb (GET, POST, PUT, DELETE, PATCH).
    query_text   : Full search query string (for SEARCH actions only).
    resource_id  : Primary resource identifier touched by the request
                   (crime_id, criminal_id, etc.).
    ip_address   : Client IP (IPv4 or IPv6, max 45 chars).
    user_agent   : HTTP User-Agent header (truncated to 500 chars).
    status_code  : HTTP response status code.
    duration_ms  : End-to-end request latency in milliseconds.
    created_at   : UTC timestamp of the request (server default).
    """

    __tablename__ = "audit_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), nullable=True, index=True)
    badge_number = Column(String(50), nullable=True)
    action       = Column(
        SAEnum(
            AuditAction,
            name="audit_action",
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    endpoint     = Column(String(500), nullable=False)
    method       = Column(String(10), nullable=False)
    query_text   = Column(Text, nullable=True)
    resource_id  = Column(String(255), nullable=True)
    ip_address   = Column(String(45), nullable=True)
    user_agent   = Column(String(500), nullable=True)
    status_code  = Column(Integer, nullable=True)
    duration_ms  = Column(Float, nullable=True)
    created_at   = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # Composite index for common admin query: "all searches by officer X"
        Index("ix_audit_logs_user_action", "user_id", "action"),
        # Composite index for time-range scans
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog badge={self.badge_number!r} "
            f"action={self.action!r} endpoint={self.endpoint!r}>"
        )
