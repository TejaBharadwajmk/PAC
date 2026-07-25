"""
PAC — Audit Repository

Provides fire-and-forget audit log writes and admin query methods.
All methods open their own short-lived session so they are safe to
call from background tasks without sharing the request's session.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditRepository:
    """
    Repository for reading and writing audit log records.

    Write path  : inject a session from background task context.
    Query path  : inject a session from the request dependency.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(self, entry: AuditLog) -> None:
        """
        Persist a single audit log entry.

        Intentionally swallows all exceptions — audit infrastructure
        must never propagate failures to the caller.
        """
        try:
            self.db.add(entry)
            await self.db.commit()
        except Exception as exc:
            logger.warning(f"Audit log write failed (non-fatal): {exc}")
            await self.db.rollback()

    async def list_logs(
        self,
        action: Optional[AuditAction] = None,
        user_id: Optional[UUID] = None,
        badge_number: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Return a filtered, paginated list of audit records (newest first)."""
        filters = []
        if action:
            filters.append(AuditLog.action == action)
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if badge_number:
            filters.append(AuditLog.badge_number == badge_number)
        if date_from:
            filters.append(AuditLog.created_at >= date_from)
        if date_to:
            filters.append(AuditLog.created_at <= date_to)

        stmt = (
            select(AuditLog)
            .where(and_(*filters) if filters else True)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_activity(
        self,
        badge_number: str,
        limit: int = 200,
    ) -> List[AuditLog]:
        """Return all recent audit entries for a specific officer badge."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.badge_number == badge_number)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_search_queries(self, limit: int = 200) -> List[AuditLog]:
        """Return all SEARCH-action audit entries (includes query_text)."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == AuditAction.SEARCH)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
