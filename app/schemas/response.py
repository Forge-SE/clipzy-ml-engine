"""Pydantic schemas for API responses."""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper."""

    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation successful",
                "data": None,
                "error": None,
                "timestamp": "2024-04-05T10:30:00"
            }
        }


class ErrorResponse(BaseModel):
    """Error response details."""

    detail: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    success: bool
    message: str
    data: list[T]
    total: int
    page: int
    page_size: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
