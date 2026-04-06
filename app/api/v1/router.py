"""API v1 router."""

from fastapi import APIRouter

from .endpoints import health_router, jobs_router, videos_router

router = APIRouter()

# Include all endpoint routers
router.include_router(health_router)
router.include_router(videos_router)
router.include_router(jobs_router)

__all__ = ["router"]
