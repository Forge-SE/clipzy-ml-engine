"""Job management endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.exceptions import JobNotFoundError
from app.core.logging_config import get_logger
from app.schemas import (
    APIResponse,
    JobCreateRequest,
    JobDetailResponse,
    JobListResponse,
    JobResponse,
)
from app.services import get_job_service

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=APIResponse[JobResponse])
async def create_job(request: JobCreateRequest):

    try:
        job_service = get_job_service()

        # Verify video exists
        video = job_service.get_video(request.video_id)
        if not video:
            raise HTTPException(status_code=404, detail=f"Video not found: {request.video_id}")

        # Create job
        job = job_service.create_job(
            video_id=request.video_id,
            template_video_id=request.template_video_id,
            processing_config=request.config,
            webhook_url=request.webhook_url,
        )

        logger.info(f"Job created", extra={"job_id": job.job_id, "video_id": request.video_id})

        return APIResponse(
            success=True,
            message=f"Job created: {job.job_id}",
            data=JobResponse(
                job_id=job.job_id,
                video_id=job.video_id,
                status=job.status,
                progress_percent=job.progress_percent,
                current_stage=job.current_stage,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                template_video_id=job.template_video_id,
            ),
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create job")


@router.get("/{job_id}", response_model=APIResponse[JobResponse])
async def get_job(job_id: str):
 
    try:
        job_service = get_job_service()
        job = job_service.get_job(job_id)

        return APIResponse(
            success=True,
            message="Job retrieved",
            data=JobResponse(
                job_id=job.job_id,
                video_id=job.video_id,
                status=job.status,
                progress_percent=job.progress_percent,
                current_stage=job.current_stage,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                template_video_id=job.template_video_id,
            ),
        )

    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    except Exception as e:
        logger.error(f"Failed to get job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get job")


@router.get("/{job_id}/result", response_model=APIResponse[JobDetailResponse])
async def get_job_result(job_id: str):

    try:
        job_service = get_job_service()
        job = job_service.get_job(job_id)

        return APIResponse(
            success=True,
            message="Job result retrieved",
            data=JobDetailResponse(
                job_id=job.job_id,
                video_id=job.video_id,
                status=job.status,
                progress_percent=job.progress_percent,
                current_stage=job.current_stage,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                template_video_id=job.template_video_id,
                style_json=job.style_json,
                output_video_url=job.output_video_url,
                error=job.error,
                processing_time_seconds=(
                    (job.completed_at - job.started_at).total_seconds()
                    if job.started_at and job.completed_at
                    else None
                ),
            ),
        )

    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    except Exception as e:
        logger.error(f"Failed to get job result: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get job result")


@router.get("", response_model=APIResponse[JobListResponse])
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
  
    try:
        job_service = get_job_service()
        jobs, total = job_service.list_jobs(page=page, page_size=page_size)

        job_responses = [
            JobResponse(
                job_id=job.job_id,
                video_id=job.video_id,
                status=job.status,
                progress_percent=job.progress_percent,
                current_stage=job.current_stage,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                template_video_id=job.template_video_id,
            )
            for job in jobs
        ]

        return APIResponse(
            success=True,
            message="Jobs retrieved",
            data=JobListResponse(
                jobs=job_responses,
                total=total,
                page=page,
                page_size=page_size,
            ),
        )

    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")
