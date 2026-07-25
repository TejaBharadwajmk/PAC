"""
PAC — Audit Schemas (Pydantic v2)

Response models for the audit log admin API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.audit_log import AuditAction


class AuditLogResponse(BaseModel):
    """Single audit log entry returned by the admin API."""
    id:           UUID
    user_id:      Optional[UUID] = None
    badge_number: Optional[str] = None
    action:       AuditAction
    endpoint:     str
    method:       str
    query_text:   Optional[str] = None
    resource_id:  Optional[str] = None
    ip_address:   Optional[str] = None
    user_agent:   Optional[str] = None
    status_code:  Optional[int] = None
    duration_ms:  Optional[float] = None
    created_at:   datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""
    total_returned: int
    offset:         int
    results:        List[AuditLogResponse]
