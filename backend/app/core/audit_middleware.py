"""
PAC — Audit Middleware

A Starlette BaseHTTPMiddleware that logs every significant API request
to the audit_logs table for chain-of-custody compliance.

Design rules:
  1. Non-blocking — audit writes use asyncio.ensure_future() so the
     response is never delayed by the audit write.
  2. Zero extra DB round-trips on the hot path — user identity is
     extracted from the JWT payload only (no users table lookup).
  3. Selective — only paths in AUDIT_PATHS_PREFIX are logged.
     Health checks, docs, and OpenAPI schema routes are excluded.
  4. Exception-safe — if audit logic raises, the real response is
     still returned to the client.
"""

import asyncio
import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.database import AsyncSessionLocal
from app.models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)

# ── Paths that trigger audit logging ──────────────────────────
# Only paths that START WITH one of these prefixes are recorded.
# Health, docs, and OpenAPI schema are excluded.
AUDIT_PATHS_PREFIX = (
    "/api/v1/auth/login",
    "/api/v1/similarity/",
    "/api/v1/crimes/",
    "/api/v1/criminals/",
    "/api/v1/assistant/",
    "/api/v1/graph/",
    "/api/v1/behavior/",
    "/api/v1/predictions/",
    "/api/v1/geo/",
)

# Paths to always SKIP even if they match a prefix above
AUDIT_SKIP_EXACT = {
    "/health",
    "/api/v1/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}


def _should_audit(path: str) -> bool:
    if path in AUDIT_SKIP_EXACT:
        return False
    return any(path.startswith(prefix) for prefix in AUDIT_PATHS_PREFIX)


def _classify_action(method: str, path: str) -> AuditAction:
    """Map HTTP method + path to a semantic AuditAction."""
    p = path.lower()
    if "auth/login" in p:
        return AuditAction.LOGIN
    if "auth/logout" in p:
        return AuditAction.LOGOUT
    if "similarity/search" in p:
        return AuditAction.SEARCH
    if "similarity/reindex" in p:
        return AuditAction.REINDEX
    if "assistant" in p:
        return AuditAction.AI_QUERY
    m = method.upper()
    if m in ("GET", "HEAD"):
        return AuditAction.VIEW
    if m == "POST":
        return AuditAction.CREATE
    if m in ("PUT", "PATCH"):
        return AuditAction.UPDATE
    if m == "DELETE":
        return AuditAction.DELETE
    return AuditAction.VIEW


def _extract_identity(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract (user_id, badge_number) from the Authorization Bearer JWT.

    Returns (None, None) if the token is absent or invalid.
    No database call is made — we decode the payload without verification
    (the actual signature was already verified by get_current_user).
    """
    import base64
    import json as _json

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None
    token = auth_header[7:]
    try:
        # JWT is header.payload.signature — we only need the payload segment
        parts = token.split(".")
        if len(parts) != 3:
            return None, None
        # Add padding required by base64
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = _json.loads(payload_bytes)
        user_id = payload.get("sub")
        badge   = payload.get("badge") or payload.get("badge_number")
        return user_id, badge
    except Exception:
        return None, None


def _get_client_ip(request: Request) -> str:
    """Return client IP, respecting X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _write_audit(entry: AuditLog) -> None:
    """Open a dedicated session and persist the audit entry."""
    try:
        async with AsyncSessionLocal() as session:
            session.add(entry)
            await session.commit()
    except Exception as exc:
        logger.warning(f"Audit log background write failed (non-fatal): {exc}")


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that asynchronously records auditable API actions.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if not _should_audit(path):
            return await call_next(request)

        # Capture start time and identity BEFORE the handler runs
        start = time.monotonic()
        user_id, badge_number = _extract_identity(request)
        action = _classify_action(request.method, path)

        # Parse request body if needed for LOGIN or SEARCH
        query_text: Optional[str] = None
        if action == AuditAction.SEARCH:
            query_text = request.query_params.get("query_text")

        if request.method in ("POST", "PUT", "PATCH") and (badge_number is None or query_text is None):
            try:
                import json as _json
                body_bytes = await request.body()
                if body_bytes:
                    body_json = _json.loads(body_bytes)
                    if isinstance(body_json, dict):
                        if badge_number is None:
                            badge_number = body_json.get("badge_number") or body_json.get("badge")
                        if action == AuditAction.SEARCH and not query_text:
                            query_text = body_json.get("query_text")
            except Exception:
                pass

        # Extract resource_id from path (e.g. /crimes/{id})
        path_parts = [p for p in path.split("/") if p]
        resource_id: Optional[str] = None
        if len(path_parts) >= 4:
            candidate = path_parts[-1]
            # Only capture if it looks like a UUID or FIR string (not a verb)
            if candidate not in ("search", "stats", "me", "login", "refresh", "logs"):
                resource_id = candidate[:255]

        # Call the actual route handler
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            status_code = 500
            raise exc
        finally:
            duration_ms = (time.monotonic() - start) * 1000

            entry = AuditLog(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id) if user_id else None,
                badge_number=badge_number,
                action=action,
                endpoint=path[:500],
                method=request.method,
                query_text=query_text,
                resource_id=resource_id,
                ip_address=_get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:500],
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Fire-and-forget — never block the response
            asyncio.ensure_future(_write_audit(entry))

        return response
