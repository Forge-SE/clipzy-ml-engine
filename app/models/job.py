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
    result_paths: dict[str, str] = field(default_factory=dict)
    render_metadata: Optional[dict[str, Any]] = None
    logs: list[dict[str, Any]] = field(default_factory=list)
    stage_history: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[dict[str, Any]] = None
    webhook_url: Optional[str] = None
    processing_config: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def generate_id() -> str:
        """Generate a unique job ID."""
        return f"job_{uuid.uuid4().hex[:12]}"

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create Job from dictionary (for RabbitMQ deserialization)."""
        # Convert string status to enum if needed
        status = data.get("status", JobStatus.QUEUED)
        if isinstance(status, str):
            status = JobStatus(status)
        
        # Convert string current_stage to enum if needed
        current_stage = data.get("current_stage")
        if isinstance(current_stage, str):
            current_stage = ProcessingStage(current_stage)
        
        # Convert ISO format strings to datetime if needed
        created_at = data.get("created_at", datetime.utcnow())
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get("updated_at", datetime.utcnow())
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        
        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        
        return cls(
            job_id=data.get("job_id", cls.generate_id()),
            video_id=data.get("video_id", ""),
            status=status,
            progress_percent=data.get("progress_percent", 0),
            current_stage=current_stage,
            created_at=created_at,
            updated_at=updated_at,
            started_at=started_at,
            completed_at=completed_at,
            template_video_id=data.get("template_video_id"),
            style_json=data.get("style_json"),
            output_video_url=data.get("output_video_url"),
            result_paths=data.get("result_paths", {}),
            render_metadata=data.get("render_metadata"),
            logs=data.get("logs", []),
            stage_history=data.get("stage_history", []),
            error=data.get("error"),
            webhook_url=data.get("webhook_url"),
            processing_config=data.get("processing_config", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        # Handle status being either enum or string
        status_value = self.status.value if isinstance(self.status, JobStatus) else self.status
        current_stage_value = self.current_stage.value if isinstance(self.current_stage, ProcessingStage) and self.current_stage else self.current_stage
        
        return {
            "job_id": self.job_id,
            "video_id": self.video_id,
            "status": status_value,
            "progress_percent": self.progress_percent,
            "current_stage": current_stage_value,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "started_at": self.started_at.isoformat() if isinstance(self.started_at, datetime) and self.started_at else self.started_at,
            "completed_at": self.completed_at.isoformat() if isinstance(self.completed_at, datetime) and self.completed_at else self.completed_at,
            "template_video_id": self.template_video_id,
            "style_json": self.style_json,
            "output_video_url": self.output_video_url,
            "result_paths": self.result_paths,
            "render_metadata": self.render_metadata,
            "logs": self.logs,
            "stage_history": self.stage_history,
            "error": self.error,
            "webhook_url": self.webhook_url,
            "processing_config": self.processing_config,
        }
