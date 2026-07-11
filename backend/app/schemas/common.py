"""
PAC — Common Response Schemas

Shared Pydantic models used across multiple routers.
"""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response envelope."""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class MessageResponse(BaseModel):
    """Simple success/info message response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response body."""
    error: str
    status_code: int
    details: Optional[dict] = None
