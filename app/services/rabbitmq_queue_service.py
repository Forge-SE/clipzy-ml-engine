"""RabbitMQ queue service for async job processing."""

import json
from typing import Optional

import pika
from pika import BasicProperties

from app.core.config import settings
from app.core.constants import JobStatus
from app.core.exceptions import QueueError
from app.core.logging_config import get_logger
from app.models import Job

logger = get_logger(__name__)


class RabbitMQQueueService:
    """Manages RabbitMQ queue for async job processing."""

    # Queue names
    JOB_QUEUE = "video_processing_jobs"
    PRIORITY_QUEUE = "priority_jobs"
    DEAD_LETTER_QUEUE = "failed_jobs"

    def __init__(self, rabbitmq_url: str = None):
        """Initialize RabbitMQ queue service."""
        rabbitmq_url = rabbitmq_url or settings.RABBITMQ_URL
        try:
            # Parse the connection URL
            self.connection = pika.BlockingConnection(
                pika.URLParameters(rabbitmq_url)
            )
            self.channel = self.connection.channel()

            # Declare queues
            self._declare_queues()
            logger.info("Connected to RabbitMQ queue")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise QueueError(f"Failed to connect to RabbitMQ: {str(e)}")

    def _declare_queues(self):
        """Declare all required queues with proper configuration."""
        # Main job queue (durable)
        self.channel.queue_declare(
            queue=self.JOB_QUEUE,
            durable=True,
            arguments={
                'x-message-ttl': 86400000,  # 24 hour TTL
                'x-dead-letter-exchange': '',
                'x-dead-letter-routing-key': self.DEAD_LETTER_QUEUE,
            }
        )

        # Priority queue for urgent jobs
        self.channel.queue_declare(
            queue=self.PRIORITY_QUEUE,
            durable=True,
            arguments={
                'x-max-priority': 10,
                'x-dead-letter-exchange': '',
                'x-dead-letter-routing-key': self.DEAD_LETTER_QUEUE,
            }
        )

        # Dead letter queue for failed jobs
        self.channel.queue_declare(
            queue=self.DEAD_LETTER_QUEUE,
            durable=True
        )

        logger.info("Queues declared successfully")

    def enqueue_job(self, job: Job, priority: int = 0) -> bool:
        """
        Enqueue a job for processing.

        Args:
            job: Job object to enqueue
            priority: Priority level (0-10, higher = more urgent)

        Returns:
            True if successful
        """
        try:
            queue_name = self.PRIORITY_QUEUE if priority > 0 else self.JOB_QUEUE
            
            # Store job data and status in Redis (for state management)
            self.set_job_data(job.job_id, job.to_dict())
            self.set_job_status(job.job_id, job.status.value)
            
            # Prepare message
            message = json.dumps(job.to_dict())
            
            # Set message properties
            properties = BasicProperties(
                delivery_mode=2,  # Persistent message
                priority=priority if priority > 0 else None,
                content_type='application/json'
            )

            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message,
                properties=properties
            )

            logger.info(
                f"Job enqueued",
                extra={"job_id": job.job_id, "queue": queue_name}
            )
            return True

        except Exception as e:
            logger.error(f"Failed to enqueue job: {str(e)}", extra={"job_id": job.job_id})
            raise QueueError(f"Failed to enqueue job: {str(e)}")

    def dequeue_job(self, timeout: int = 1) -> Optional[Job]:
        """
        Dequeue a job for processing.

        Args:
            timeout: Timeout in seconds

        Returns:
            Job object or None if no job available
        """
        try:
            # Try priority queue first
            method, properties, body = self.channel.basic_get(
                queue=self.PRIORITY_QUEUE,
                auto_ack=False
            )

            if not method:
                # Try main queue
                method, properties, body = self.channel.basic_get(
                    queue=self.JOB_QUEUE,
                    auto_ack=False
                )

            if method:
                job_data = json.loads(body)
                job = Job.from_dict(job_data)
                
                # Acknowledge the message
                self.channel.basic_ack(delivery_tag=method.delivery_tag)
                
                logger.info(f"Job dequeued", extra={"job_id": job.job_id})
                return job

            return None

        except Exception as e:
            logger.error(f"Failed to dequeue job: {str(e)}")
            raise QueueError(f"Failed to dequeue job: {str(e)}")

    def set_job_status(self, job_id: str, status: str) -> bool:
        """
        Set job status (would typically use Redis for this).

        Args:
            job_id: Job ID
            status: Status value

        Returns:
            True if successful
        """
        try:
            # Using Redis for status tracking
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.set(f"job_status:{job_id}", status)
            return True

        except Exception as e:
            logger.error(f"Failed to set job status: {str(e)}")
            raise QueueError(f"Failed to set job status: {str(e)}")

    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get job status from Redis."""
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            status = redis_client.get(f"job_status:{job_id}")
            return status

        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            raise QueueError(f"Failed to get job status: {str(e)}")

    def nack_job(self, job_id: str, requeue: bool = True):
        """
        Negative acknowledge a job (mark as failed or requeue).

        Args:
            job_id: Job ID
            requeue: Whether to requeue the job
        """
        try:
            logger.info(
                f"Job nacked",
                extra={"job_id": job_id, "requeue": requeue}
            )
        except Exception as e:
            logger.error(f"Failed to nack job: {str(e)}")
            raise QueueError(f"Failed to nack job: {str(e)}")

    def get_queue_size(self, queue_name: str = None) -> int:
        """Get the size of a queue."""
        try:
            queue_name = queue_name or self.JOB_QUEUE
            method = self.channel.queue_declare(queue=queue_name, passive=True)
            return method.method.message_count

        except Exception as e:
            logger.error(f"Failed to get queue size: {str(e)}")
            raise QueueError(f"Failed to get queue size: {str(e)}")

    def purge_queue(self, queue_name: str = None) -> bool:
        """Purge all messages from a queue (USE WITH CAUTION)."""
        try:
            queue_name = queue_name or self.JOB_QUEUE
            self.channel.queue_purge(queue=queue_name)
            logger.warning(f"Queue purged: {queue_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to purge queue: {str(e)}")
            raise QueueError(f"Failed to purge queue: {str(e)}")

    def set_job_data(self, job_id: str, data: dict) -> bool:
        """Store full job data in Redis."""
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.set(job_id, json.dumps(data))
            return True

        except Exception as e:
            logger.error(f"Failed to set job data: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to set job data: {str(e)}")

    def get_job_data(self, job_id: str) -> Optional[dict]:
        """Retrieve full job data from Redis."""
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            data = redis_client.get(job_id)
            return json.loads(data) if data else None

        except Exception as e:
            logger.error(f"Failed to get job data: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to get job data: {str(e)}")

    def set_job_result(self, job_id: str, result: dict) -> bool:
        """Store job result in Redis."""
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.set(f"job_result:{job_id}", json.dumps(result))
            return True

        except Exception as e:
            logger.error(f"Failed to set job result: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to set job result: {str(e)}")

    def get_job_result(self, job_id: str) -> Optional[dict]:
        """Retrieve job result from Redis."""
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            result = redis_client.get(f"job_result:{job_id}")
            return json.loads(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get job result: {str(e)}", extra={"job_id": job_id})
            raise QueueError(f"Failed to get job result: {str(e)}")

    def close(self):
        """Close the RabbitMQ connection."""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
