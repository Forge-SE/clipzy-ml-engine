"""Queue service factory supporting both Redis and RabbitMQ."""

import json
from typing import Optional

import redis

from app.core.config import settings
from app.core.constants import JOB_QUEUE_KEY, JOB_RESULT_PREFIX, JOB_STATUS_PREFIX, JobStatus
from app.core.exceptions import QueueError
from app.core.logging_config import get_logger
from app.models import Job

logger = get_logger(__name__)


class RedisQueueService:
    """Redis queue backend."""

    def __init__(self, redis_url: str = None):
        """Initialize queue service with Redis connection."""
        redis_url = redis_url or settings.REDIS_URL
        try:
            self.redis_client = redis.from_url(
                redis_url,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis queue")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise QueueError(f"Failed to connect to Redis: {str(e)}")

    def enqueue_job(self, job: Job) -> bool:
        try:
            # Store job details
            self.set_job_status(job.job_id, job.status.value)
            self.set_job_data(job.job_id, job.to_dict())
            self.redis_client.rpush(JOB_QUEUE_KEY, job.job_id)

            logger.info(f"Job enqueued", extra={"job_id": job.job_id})
            return True

        except Exception as e:
            logger.error(f"Failed to enqueue job: {str(e)}", extra={"job_id": job.job_id})
            raise QueueError(f"Failed to enqueue job: {str(e)}")

    def dequeue_job(self) -> Optional[str]:
        try:
            job_id = self.redis_client.lpop(JOB_QUEUE_KEY)
            if job_id:
                logger.info(f"Job dequeued", extra={"job_id": job_id})
            return job_id

        except Exception as e:
            logger.error(f"Failed to dequeue job: {str(e)}")
            raise QueueError(f"Failed to dequeue job: {str(e)}")

    def set_job_status(self, job_id: str, status: str) -> bool:
        """Set job status in Redis."""
        try:
            self.redis_client.set(f"{JOB_STATUS_PREFIX}{job_id}", status)
            return True

        except Exception as e:
            logger.error(f"Failed to set job status: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to set job status: {str(e)}")

    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get job status from Redis."""
        try:
            status = self.redis_client.get(f"{JOB_STATUS_PREFIX}{job_id}")
            return status

        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to get job status: {str(e)}")

    def set_job_data(self, job_id: str, data: dict) -> bool:
        """Store full job data in Redis."""
        try:
            self.redis_client.set(job_id, json.dumps(data))
            return True

        except Exception as e:
            logger.error(f"Failed to set job data: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to set job data: {str(e)}")

    def get_job_data(self, job_id: str) -> Optional[dict]:
        """Retrieve full job data from Redis."""
        try:
            data = self.redis_client.get(job_id)
            return json.loads(data) if data else None

        except Exception as e:
            logger.error(f"Failed to get job data: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to get job data: {str(e)}")

    def set_job_result(self, job_id: str, result: dict) -> bool:
        """Store job result in Redis."""
        try:
            self.redis_client.set(f"{JOB_RESULT_PREFIX}{job_id}", json.dumps(result))
            return True

        except Exception as e:
            logger.error(f"Failed to set job result: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to set job result: {str(e)}")

    def get_job_result(self, job_id: str) -> Optional[dict]:
        """Retrieve job result from Redis."""
        try:
            result = self.redis_client.get(f"{JOB_RESULT_PREFIX}{job_id}")
            return json.loads(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get job result: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to get job result: {str(e)}")

    def delete_job(self, job_id: str) -> bool:
        """Delete job from Redis."""
        try:
            self.redis_client.delete(job_id, f"{JOB_STATUS_PREFIX}{job_id}", f"{JOB_RESULT_PREFIX}{job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete job: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to delete job: {str(e)}")

    def queue_size(self) -> int:
        """Get the number of jobs in the queue."""
        try:
            return self.redis_client.llen(JOB_QUEUE_KEY)

        except Exception as e:
            logger.error(f"Failed to get queue size: {str(e)}")
            raise QueueError(f"Failed to get queue size: {str(e)}")

    def clear_queue(self) -> bool:
        """Clear all jobs from the queue (use with caution)."""
        try:
            self.redis_client.delete(JOB_QUEUE_KEY)
            logger.warning("Queue cleared")
            return True

        except Exception as e:
            logger.error(f"Failed to clear queue: {str(e)}")
            raise QueueError(f"Failed to clear queue: {str(e)}")


class QueueService:
    """Factory queue service supporting multiple backends."""

    def __init__(self, backend: str = "redis"):
        """
        Initialize queue service with specified backend.

        Args:
            backend: 'redis' or 'rabbitmq'
        """
        if backend == "rabbitmq":
            try:
                from app.services.rabbitmq_queue_service import RabbitMQQueueService
                self._service = RabbitMQQueueService()
            except ImportError:
                logger.warning("RabbitMQ not available, falling back to Redis")
                self._service = RedisQueueService()
        else:
            self._service = RedisQueueService()

    def enqueue_job(self, job: Job) -> bool:
        return self._service.enqueue_job(job)

    def dequeue_job(self) -> Optional[str]:
        return self._service.dequeue_job()

    def set_job_status(self, job_id: str, status: str) -> bool:
        return self._service.set_job_status(job_id, status)

    def get_job_status(self, job_id: str) -> Optional[str]:
        return self._service.get_job_status(job_id)

    def set_job_data(self, job_id: str, data: dict) -> bool:
        return self._service.set_job_data(job_id, data)

    def get_job_data(self, job_id: str) -> Optional[dict]:
        return self._service.get_job_data(job_id)

    def set_job_result(self, job_id: str, result: dict) -> bool:
        return self._service.set_job_result(job_id, result)

    def get_job_result(self, job_id: str) -> Optional[dict]:
        return self._service.get_job_result(job_id)

    def delete_job(self, job_id: str) -> bool:
        return self._service.delete_job(job_id)

    def queue_size(self) -> int:
        return self._service.queue_size()

    def clear_queue(self) -> bool:
        return self._service.clear_queue()


# Global queue service instance (uses Redis by default)
_queue_service: Optional[QueueService] = None


def get_queue_service() -> QueueService:
    """Get or create the queue service instance."""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService(backend="rabbitmq")
    return _queue_service
