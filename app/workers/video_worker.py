"""Video processing worker that processes jobs from the queue."""

import signal
import sys
import time
from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_logger, setup_logging
from app.services import get_queue_service
from app.workers.tasks import process_video_job

logger = get_logger(__name__)


class VideoWorker:
    """Worker that processes video jobs from the Redis queue."""

    def __init__(self, worker_id: str = "worker-1"):
        """
        Initialize the worker.

        Args:
            worker_id: Unique identifier for this worker
        """
        self.worker_id = worker_id
        self.queue_service = get_queue_service()
        self.running = True
        self.processed_count = 0
        self.failed_count = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logger.info(f"Worker initialized", extra={"worker_id": worker_id})

    def start(self, poll_interval: int = 5) -> None:
        """
        Start the worker and begin processing jobs.

        Args:
            poll_interval: Seconds to wait between queue checks
        """
        logger.info(f"Worker starting", extra={"worker_id": self.worker_id})

        while self.running:
            try:
                # Try to get a job from the queue
                job_id = self.queue_service.dequeue_job()

                if job_id:
                    logger.info(
                        f"Processing job",
                        extra={"worker_id": self.worker_id, "job_id": job_id}
                    )

                    try:
                        # Process the job
                        process_video_job(job_id)
                        self.processed_count += 1

                        logger.info(
                            f"Job processed successfully",
                            extra={
                                "worker_id": self.worker_id,
                                "job_id": job_id,
                                "total_processed": self.processed_count
                            }
                        )

                    except Exception as e:
                        self.failed_count += 1
                        logger.error(
                            f"Job processing failed",
                            extra={
                                "worker_id": self.worker_id,
                                "job_id": job_id,
                                "error": str(e),
                                "total_failed": self.failed_count
                            }
                        )

                else:
                    # Queue is empty, wait before checking again
                    time.sleep(poll_interval)

            except Exception as e:
                logger.error(
                    f"Worker error",
                    extra={"worker_id": self.worker_id, "error": str(e)}
                )
                time.sleep(poll_interval)

        logger.info(
            f"Worker stopped",
            extra={
                "worker_id": self.worker_id,
                "processed": self.processed_count,
                "failed": self.failed_count
            }
        )

    def _handle_shutdown(self, signum: int, frame: Optional[object]) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Shutdown signal received", extra={"worker_id": self.worker_id})
        self.running = False


def run_worker(worker_id: str = "worker-1", poll_interval: int = 5) -> None:
    """
    Run a video processing worker.

    This is the entrypoint for running workers.

    Args:
        worker_id: Unique identifier for this worker
        poll_interval: Seconds to wait between queue checks
    """
    setup_logging(level=settings.LOG_LEVEL)
    worker = VideoWorker(worker_id=worker_id)
    worker.start(poll_interval=poll_interval)
