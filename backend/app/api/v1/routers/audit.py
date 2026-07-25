"""
PAC — Audit Log Admin Router

Admin-only endpoints for querying the audit trail.
All endpoints require ADMIN role.

Endpoints:
  GET /api/v1/audit/logs                       — Paginated, filtered audit log
  GET /api/v1/audit/logs/user/{badge_number}   — Activity for a specific officer
  GET /api/v1/audit/logs/search                — All similarity search queries
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import DbSession, require_roles
from app.models.audit_log import AuditAction
from app.models.user import UserRole
from app.repositories.audit_repo import AuditRepository
from app.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter()

_admin_only = Depends(require_roles(UserRole.ADMIN))


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="Query audit logs (admin only)",
    description=(
        "Paginated, filterable audit trail. Supports filtering by:\\n\\n"
        "- `action` — one of: login, logout, search, view, create, update, delete, reindex, ai_query\\n"
        "- `badge_number` — exact officer badge\\n"
        "- `date_from` / `date_to` — ISO-8601 datetime range\\n\\n"
        "Results are ordered newest-first."
    ),
    dependencies=[_admin_only],
)
async def list_audit_logs(
    db: DbSession,
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    badge_number: Optional[str] = Query(None, description="Filter by officer badge number"),
    date_from: Optional[datetime] = Query(None, description="Include records on or after this datetime (ISO-8601)"),
    date_to: Optional[datetime] = Query(None, description="Include records on or before this datetime (ISO-8601)"),
    limit: int = Query(default=100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
):
    repo = AuditRepository(db)
    logs = await repo.list_logs(
        action=action,
        badge_number=badge_number,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        total_returned=len(logs),
        offset=offset,
        results=logs,
    )


@router.get(
    "/logs/user/{badge_number}",
    response_model=AuditLogListResponse,
    summary="Officer activity timeline (admin only)",
    description="Returns full audit history for a specific officer, newest-first.",
    dependencies=[_admin_only],
)
async def get_officer_activity(
    badge_number: str,
    db: DbSession,
    limit: int = Query(default=200, ge=1, le=500),
):
    repo = AuditRepository(db)
    logs = await repo.get_user_activity(badge_number=badge_number, limit=limit)
    return AuditLogListResponse(
        total_returned=len(logs),
        offset=0,
        results=logs,
    )


@router.get(
    "/logs/search",
    response_model=AuditLogListResponse,
    summary="All similarity search queries (admin only)",
    description=(
        "Returns all audit entries with action=search. "
        "The `query_text` field contains the exact text submitted to the "
        "similarity engine, enabling review of investigative intelligence queries."
    ),
    dependencies=[_admin_only],
)
async def get_search_queries(
    db: DbSession,
    limit: int = Query(default=200, ge=1, le=500),
):
    repo = AuditRepository(db)
    logs = await repo.get_search_queries(limit=limit)
    return AuditLogListResponse(
        total_returned=len(logs),
        offset=0,
        results=logs,
    )
