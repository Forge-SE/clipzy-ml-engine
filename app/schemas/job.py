"""Job-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.constants import JobStatus, ProcessingStage
class JobProgressUpdate(BaseModel):
    """Progress update for a job."""

    stage: ProcessingStage
    progress_percent: int = Field(..., ge=0, le=100)
    status: str = Field(default="in_progress")
    message: Optional[str] = None


class JobProcessingError(BaseModel):
    """Processing error details."""

    stage: Optional[str] = None
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime


class JobLogEntry(BaseModel):
    """Single log entry attached to a job."""

    timestamp: datetime
    level: str
    message: str
    stage: Optional[str] = None


class JobStageEvent(BaseModel):
    """Stage transition history for a job."""

    timestamp: datetime
    status: str
    progress_percent: int
    stage: Optional[str] = None


class JobCreateRequest(BaseModel):
    """Request to create a job."""

    video_id: str = Field(..., description="ID of the video to process")
    template_video_id: Optional[str] = Field(
        None,
        description="Optional template video for style reference"
    )
    config: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional processing configuration"
    )
    webhook_url: Optional[str] = Field(
        None,
        description="Optional webhook URL to notify on completion"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "vid_abc123def456",
                "template_video_id": None,
                "config": {"quality": "high", "output_format": "mp4"},
                "webhook_url": "https://example.com/webhook"
            }
        }


class JobResponse(BaseModel):
    """Job response model."""

    job_id: str
    video_id: str
    status: JobStatus
    progress_percent: int = Field(default=0, ge=0, le=100)
    current_stage: Optional[ProcessingStage] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    template_video_id: Optional[str] = None
    style_json: Optional[dict[str, Any]] = None
    output_video_url: Optional[str] = None
    result_paths: dict[str, str] = Field(default_factory=dict)
    render_metadata: Optional[dict[str, Any]] = None
    logs: list[JobLogEntry] = Field(default_factory=list)
    stage_history: list[JobStageEvent] = Field(default_factory=list)
    error: Optional[JobProcessingError] = None
    processing_time_seconds: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_xyz789abc123",
                "video_id": "vid_abc123def456",
                "status": "processing",
                "progress_percent": 45,
                "current_stage": "video_analysis",
                "created_at": "2024-04-05T10:30:00Z",
                "updated_at": "2024-04-05T10:35:00Z",
                "started_at": "2024-04-05T10:31:00Z",
                "completed_at": None,
                "template_video_id": None
            }
        }


class JobDetailResponse(JobResponse):
    """Detailed job response including results."""

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_xyz789abc123",
                "video_id": "vid_abc123def456",
                "status": "completed",
                "progress_percent": 100,
                "current_stage": "rendering",
                "created_at": "2024-04-05T10:30:00Z",
                "updated_at": "2024-04-05T10:45:00Z",
                "started_at": "2024-04-05T10:31:00Z",
                "completed_at": "2024-04-05T10:45:00Z",
                "template_video_id": None,
                "style_json": {
                    "version": "1.0",
                    "color_grade": {
                        "temperature": 10,
                        "tint": 5,
                        "saturation": 20,
                        "contrast": 15,
                        "highlights": 10,
                        "shadows": -5,
                    },
                    "aspect_ratio": "16:9",
                    "frame_rate": 30,
                    "audio_style": {
                        "normalization_level": 0.85,
                        "compression_ratio": 4.0,
                        "bass_boost": 20,
                        "enhance_speech": True,
                    },
                    "cut_frequency": 3.5,
                    "motion_intensity": 65,
                    "zoom_usage": 30,
                    "primary_transition": {
                        "type": "fade",
                        "duration_ms": 300,
                        "easing": "ease-in-out",
                    },
                    "detected_beats": [],
                    "created_at": "2024-04-05T10:31:00Z",
                    "source_duration_seconds": 60.0,
                    "extraction_confidence": 0.92,
                },
                "output_video_url": "file:///storage/job_xyz789abc123/output.mp4",
                "processing_time_seconds": 900.0,
            }
        }


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int

    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [
                    {
                        "job_id": "job_xyz789abc123",
                        "video_id": "vid_abc123def456",
                        "status": "completed",
                        "progress_percent": 100,
                        "current_stage": "rendering",
                        "created_at": "2024-04-05T10:30:00Z",
                        "updated_at": "2024-04-05T10:45:00Z",
                        "started_at": "2024-04-05T10:31:00Z",
                        "completed_at": "2024-04-05T10:45:00Z",
                        "template_video_id": None
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10
            }
        }
