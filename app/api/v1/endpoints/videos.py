"""Video upload and management endpoints."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.core.config import settings
from app.core.exceptions import InvalidVideoError, StorageError
from app.core.logging_config import get_logger
from app.schemas import APIResponse, VideoUploadResponse, VideoMetadata
from app.services import get_job_service, get_storage_service
from app.utils.validators import validate_video_file

logger = get_logger(__name__)
router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=APIResponse[VideoUploadResponse])
async def upload_video(
    file: UploadFile = File(...),
    template_video_id: Optional[str] = Form(None),
    webhook_url: Optional[str] = Form(None),
):
 
    try:
        # Validate file
        if not file.filename:
            raise InvalidVideoError("No filename provided")

        # Read and validate video
        content = await file.read()

        if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise InvalidVideoError(
                f"File size exceeds maximum of {settings.MAX_FILE_SIZE_MB}MB"
            )

        # Validate video format
        validate_video_file(file.filename, content)

        # Upload to S3 directly
        storage_service = get_storage_service()
        storage_url = storage_service.upload(
            file_content=content,
            destination_folder="videos",
            filename=file.filename,
        )

        # Get video metadata (stub for now)
        metadata = VideoMetadata(
            width=1920,
            height=1080,
            duration_seconds=60.0,
            frame_rate=30.0,
            codec="h264",
            bitrate_kbps=5000,
            format=file.filename.split(".")[-1].lower(),
        )

        # Store video in job service
        job_service = get_job_service()
        video = job_service.store_video(
            filename=file.filename,
            file_size_bytes=len(content),
            storage_path=storage_url,  # Use S3 URL
            metadata=metadata.model_dump(),
        )

        # Create processing job with storage path
        job = job_service.create_job(
            video_id=video.video_id,
            template_video_id=template_video_id,
            webhook_url=webhook_url,
            processing_config={
                "storage_path": storage_url,
                "filename": file.filename,
                "file_size_bytes": len(content),
            }
        )

        logger.info(
            f"Video uploaded and job created",
            extra={"video_id": video.video_id, "job_id": job.job_id}
        )

        # Prepare response
        response_data = VideoUploadResponse(
            job_id=job.job_id,
            video_id=video.video_id,
            filename=video.filename,
            file_size_bytes=video.file_size_bytes,
            metadata=metadata,
            uploaded_at=video.uploaded_at,
            storage_url=video.storage_path,
        )

        return APIResponse(
            success=True,
            message=f"Video uploaded successfully. Job created: {job.job_id}",
            data=response_data,
        )

    except InvalidVideoError as e:
        logger.warning(f"Invalid video upload: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)

    except StorageError as e:
        logger.error(f"Storage error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store video")

    except Exception as e:
        logger.error(f"Video upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload video")


@router.get("/info/{video_id}")
async def get_video_info(video_id: str):
    """Get information about an uploaded video."""
    try:
        job_service = get_job_service()
        video = job_service.get_video(video_id)

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        return APIResponse(
            success=True,
            message="Video info retrieved",
            data={
                "video_id": video.video_id,
                "filename": video.filename,
                "file_size_bytes": video.file_size_bytes,
                "metadata": video.metadata,
                "uploaded_at": video.uploaded_at.isoformat(),
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get video info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get video info")
