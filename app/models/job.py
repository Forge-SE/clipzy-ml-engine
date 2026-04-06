"""In-memory models for the application.

For production, replace with SQLAlchemy + PostgreSQL or similar.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import uuid

from app.core.constants import JobStatus, ProcessingStage


@dataclass
class Video:
    """Video entity."""

    video_id: str
    filename: str
    file_size_bytes: int
    storage_path: str
    metadata: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    uploaded_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def generate_id() -> str:
        """Generate a unique video ID."""
        return f"vid_{uuid.uuid4().hex[:12]}"


@dataclass
class Job:
    """Job entity for video processing."""

    job_id: str
    video_id: str
    status: JobStatus = JobStatus.QUEUED
    progress_percent: int = 0
    current_stage: Optional[ProcessingStage] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    template_video_id: Optional[str] = None
    style_json: Optional[dict[str, Any]] = None
    output_video_url: Optional[str] = None
    error: Optional[dict[str, Any]] = None
    webhook_url: Optional[str] = None
    processing_config: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def generate_id() -> str:
        """Generate a unique job ID."""
        return f"job_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "video_id": self.video_id,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "template_video_id": self.template_video_id,
            "style_json": self.style_json,
            "output_video_url": self.output_video_url,
            "error": self.error,
            "webhook_url": self.webhook_url,
        }
