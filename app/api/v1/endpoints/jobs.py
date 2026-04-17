"""Job management endpoints."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from app.core.exceptions import JobNotFoundError
from app.core.logging_config import get_logger
from app.schemas import (
    APIResponse,
    JobCreateRequest,
    JobDetailResponse,
    JobListResponse,
    JobResponse,
)
from app.services import get_job_service, get_storage_service

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


def _processing_time_seconds(job) -> Optional[float]:
    if job.started_at and job.completed_at:
        return (job.completed_at - job.started_at).total_seconds()
    return None


def _job_payload(job) -> dict:
    return {
        "job_id": job.job_id,
        "video_id": job.video_id,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "current_stage": job.current_stage,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "template_video_id": job.template_video_id,
        "style_json": job.style_json,
        "output_video_url": job.output_video_url,
        "result_paths": job.result_paths,
        "render_metadata": job.render_metadata,
        "logs": job.logs,
        "stage_history": job.stage_history,
        "error": job.error,
        "processing_time_seconds": _processing_time_seconds(job),
    }


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
            data=JobResponse(**_job_payload(job)),
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
            data=JobResponse(**_job_payload(job)),
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
            data=JobDetailResponse(**_job_payload(job)),
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
            JobResponse(**_job_payload(job))
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


@router.get("/{job_id}/download")
async def download_job_output(job_id: str):
    """Download or redirect to the final rendered MP4."""
    try:
        job_service = get_job_service()
        storage_service = get_storage_service()
        job = job_service.get_job(job_id)

        if not job.output_video_url:
            raise HTTPException(status_code=404, detail="Rendered output not available yet")

        if job.output_video_url.startswith("s3://"):
            download_url = storage_service.get_download_url(job.output_video_url)
            return RedirectResponse(download_url)

        file_path = Path(job.output_video_url.replace("file:///", "").replace("file://", ""))
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Rendered output file not found")

        return FileResponse(
            path=str(file_path),
            media_type="video/mp4",
            filename=file_path.name,
        )

    except HTTPException:
        raise

    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    except Exception as e:
        logger.error(f"Failed to download job output: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download job output")
