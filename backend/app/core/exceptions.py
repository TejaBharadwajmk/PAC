"""
PAC Backend — Custom Exception Classes & FastAPI Exception Handlers

All domain exceptions derive from PACException.
Exception handlers convert them to consistent JSON error responses.
"""

import logging
import socket
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

logger = logging.getLogger(__name__)


# ── Domain Exceptions ──────────────────────────────────────

class PACException(Exception):
    """Base exception for all PAC application errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(PACException):
    def __init__(self, resource: str, identifier: str = ""):
        detail = f"{resource} not found"
        if identifier:
            detail += f" [{identifier}]"
        super().__init__(message=detail, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(PACException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)


class AuthenticationError(PACException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(PACException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class ValidationError(PACException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ServiceUnavailableError(PACException):
    def __init__(self, service: str):
        super().__init__(
            message=f"Service unavailable: {service}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ── Exception Handlers ─────────────────────────────────────

def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""

    @app.exception_handler(PACException)
    async def pac_exception_handler(request: Request, exc: PACException) -> JSONResponse:
        logger.warning(f"{type(exc).__name__}: {exc.message} | {request.method} {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "status_code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"Validation error on {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Request validation failed",
                "details": exc.errors(),
                "status_code": 422,
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.error(f"DB IntegrityError: {exc.orig}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Data conflict: a record with this identifier already exists.",
                "status_code": 409,
            },
        )

    @app.exception_handler(OperationalError)
    async def operational_handler(request: Request, exc: OperationalError) -> JSONResponse:
        logger.critical(f"DB OperationalError: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Database service unavailable", "status_code": 503},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.critical(
            f"Unhandled exception: {type(exc).__name__}: {exc} | {request.method} {request.url}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "status_code": 500},
        )
