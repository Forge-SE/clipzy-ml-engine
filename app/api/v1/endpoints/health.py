"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings
from app.schemas import APIResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint."""
    return APIResponse(
        success=True,
        message="API is healthy",
        data={
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION,
        }
    )
