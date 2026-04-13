"""Job service for managing video processing jobs."""

from datetime import datetime
from typing import Optional

from app.core.constants import JobStatus, ProcessingStage
from app.core.exceptions import JobNotFoundError
from app.core.logging_config import get_logger
from app.models import Job, Video
from app.services.queue_service import get_queue_service

logger = get_logger(__name__)

# In-memory storage (replace with database in production)
_jobs_store: dict[str, Job] = {}
_videos_store: dict[str, Video] = {}


class JobService:
    """Service for managing video processing jobs."""

    def __init__(self):
        """Initialize job service."""
        self.queue_service = get_queue_service()

    def create_job(
        self,
        video_id: str,
        template_video_id: Optional[str] = None,
        processing_config: Optional[dict] = None,
        webhook_url: Optional[str] = None,
    ) -> Job:
        """
        Create a new video processing job.

        Args:
            video_id: ID of the video to process
            template_video_id: Optional template video ID for style reference
            processing_config: Optional processing configuration
            webhook_url: Optional webhook URL for completion notification

        Returns:
            Created Job object
        """
        job = Job(
            job_id=Job.generate_id(),
            video_id=video_id,
            template_video_id=template_video_id,
            webhook_url=webhook_url,
            processing_config=processing_config or {},
        )

        # Store in memory
        _jobs_store[job.job_id] = job

        # Enqueue for processing
        self.queue_service.enqueue_job(job)

        logger.info(
            f"Job created",
            extra={"job_id": job.job_id, "video_id": video_id}
        )

        return job

    def get_job(self, job_id: str) -> Job:
        """
        Get a job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job object

        Raises:
            JobNotFoundError: If job not found
        """
        # Try Redis first (has updated status during processing)
        job_data = self.queue_service.get_job_data(job_id)
        if job_data:
            return Job.from_dict(job_data)

        # Fall back to memory if not in Redis
        if job_id in _jobs_store:
            return _jobs_store[job_id]

        # Not found anywhere
        raise JobNotFoundError(job_id)

    def list_jobs(self, page: int = 1, page_size: int = 10) -> tuple[list[Job], int]:
        """
        List all jobs with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of jobs per page

        Returns:
            Tuple of (jobs list, total count)
        """
        all_jobs = list(_jobs_store.values())
        total = len(all_jobs)

        # Sort by created_at descending
        all_jobs.sort(key=lambda j: j.created_at, reverse=True)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        paginated_jobs = all_jobs[start:end]

        return paginated_jobs, total

    def update_job_progress(
        self,
        job_id: str,
        status: JobStatus,
        progress_percent: int = 0,
        stage: Optional[ProcessingStage] = None,
    ) -> Job:
        """
        Update job progress.

        Args:
            job_id: Job ID
            status: New job status
            progress_percent: Progress percentage (0-100)
            stage: Current processing stage

        Returns:
            Updated Job object
        """
        job = self.get_job(job_id)
        job.status = status
        job.progress_percent = progress_percent
        job.current_stage = stage
        job.updated_at = datetime.utcnow()

        # Set started_at if transitioning to processing
        if job.status == JobStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.utcnow()

        # Set completed_at if transitioning to completed or failed
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            if not job.completed_at:
                job.completed_at = datetime.utcnow()

        # Update storage
        _jobs_store[job_id] = job
        self.queue_service.set_job_status(job_id, status.value)
        self.queue_service.set_job_data(job_id, job.to_dict())

        logger.info(
            f"Job progress updated",
            extra={"job_id": job_id, "status": status.value, "progress": progress_percent}
        )

        return job

    def set_job_result(
        self,
        job_id: str,
        style_json: Optional[dict] = None,
        output_video_url: Optional[str] = None,
    ) -> Job:
        """
        Set job result data.

        Args:
            job_id: Job ID
            style_json: Style JSON result
            output_video_url: Output video URL

        Returns:
            Updated Job object
        """
        job = self.get_job(job_id)
        job.style_json = style_json
        job.output_video_url = output_video_url

        _jobs_store[job_id] = job
        self.queue_service.set_job_data(job_id, job.to_dict())

        logger.info(
            f"Job result set",
            extra={"job_id": job_id, "has_style": style_json is not None, "has_output": output_video_url is not None}
        )

        return job

    def set_job_error(
        self,
        job_id: str,
        error_message: str,
        stage: Optional[ProcessingStage] = None,
        details: Optional[dict] = None,
    ) -> Job:
        """
        Set job error.

        Args:
            job_id: Job ID
            error_message: Error message
            stage: Stage where error occurred
            details: Additional error details

        Returns:
            Updated Job object
        """
        job = self.get_job(job_id)
        job.error = {
            "message": error_message,
            "stage": stage.value if stage else None,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        job = self.update_job_progress(job_id, JobStatus.FAILED)

        logger.error(
            f"Job error set",
            extra={"job_id": job_id, "error": error_message, "stage": stage}
        )

        return job

    def store_video(
        self,
        filename: str,
        file_size_bytes: int,
        storage_path: str,
        metadata: dict,
    ) -> Video:
        """
        Store video metadata.

        Args:
            filename: Video filename
            file_size_bytes: File size in bytes
            storage_path: Storage path/URL
            metadata: Video metadata

        Returns:
            Video object
        """
        video = Video(
            video_id=Video.generate_id(),
            filename=filename,
            file_size_bytes=file_size_bytes,
            storage_path=storage_path,
            metadata=metadata,
        )

        _videos_store[video.video_id] = video

        logger.info(
            f"Video stored",
            extra={"video_id": video.video_id, "filename": filename}
        )

        return video

    def get_video(self, video_id: str) -> Optional[Video]:
        """Get video by ID."""
        return _videos_store.get(video_id)

    @staticmethod
    def _job_from_dict(data: dict) -> Job:
        """Reconstruct Job from dictionary."""
        return Job.from_dict(data)


# Global job service instance
_job_service: Optional[JobService] = None


def get_job_service() -> JobService:
    """Get or create the job service instance."""
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service
