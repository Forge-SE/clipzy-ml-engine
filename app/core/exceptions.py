"""Custom exceptions for the application."""

from typing import Optional


class ClipzyException(Exception):
    """Base exception for all Clipzy errors."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class JobNotFoundError(ClipzyException):
    """Raised when a job is not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job '{job_id}' not found",
            status_code=404,
            details={"job_id": job_id}
        )


class InvalidVideoError(ClipzyException):
    """Raised when video validation fails."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid video: {reason}",
            status_code=400,
            details={"reason": reason}
        )


class StorageError(ClipzyException):
    """Raised when storage operations fail."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=500)


class QueueError(ClipzyException):
    """Raised when queue operations fail."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=500)


class ProcessingError(ClipzyException):
    """Raised when video processing fails."""

    def __init__(self, message: str, job_id: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            details={"job_id": job_id} if job_id else {}
        )
