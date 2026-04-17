"""Video-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    """Video metadata."""

    width: int = Field(..., description="Video width in pixels")
    height: int = Field(..., description="Video height in pixels")
    duration_seconds: float = Field(..., description="Video duration in seconds")
    frame_rate: float = Field(..., description="Video frame rate (fps)")
    codec: str = Field(..., description="Video codec (h264, h265, etc.)")
    bitrate_kbps: int = Field(..., description="Video bitrate in kbps")
    format: str = Field(..., description="Video format (mp4, mov, etc.)")


class UploadVideoRequest(BaseModel):
    """Request to upload a video."""

    # Note: The video file is passed via multipart form data in FastAPI
    template_video_id: Optional[str] = Field(
        None,
        description="Optional template video ID to use for style reference"
    )
    webhook_url: Optional[str] = Field(
        None,
        description="Optional webhook URL for processing completion notification"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "template_video_id": None,
                "webhook_url": "https://example.com/webhook"
            }
        }


class VideoResponse(BaseModel):
    """Video response model."""

    video_id: str
    filename: str
    file_size_bytes: int
    metadata: VideoMetadata
    storage_path: str
    uploaded_at: datetime
    status: str = "stored"


class VideoUploadResponse(BaseModel):
    """Response after video upload."""

    job_id: Optional[str] = None
    video_id: str
    filename: str
    file_size_bytes: int
    metadata: VideoMetadata
    uploaded_at: datetime
    storage_url: str

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_xyz789abc123",
                "video_id": "vid_abc123def456",
                "filename": "my_video.mp4",
                "file_size_bytes": 52428800,
                "metadata": {
                    "width": 1920,
                    "height": 1080,
                    "duration_seconds": 60.0,
                    "frame_rate": 30.0,
                    "codec": "h264",
                    "bitrate_kbps": 5000,
                    "format": "mp4"
                },
                "uploaded_at": "2024-04-05T10:30:00Z",
                "storage_url": "file:///storage/vid_abc123def456/my_video.mp4"
            }
        }
