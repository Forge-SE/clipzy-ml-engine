"""Application constants."""

from enum import Enum


class JobStatus(str, Enum):
    """Job processing status."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStage(str, Enum):
    """Video processing pipeline stages."""

    VIDEO_ANALYSIS = "video_analysis"
    AUDIO_ANALYSIS = "audio_analysis"
    MOTION_ANALYSIS = "motion_analysis"
    STYLE_EXTRACTION = "style_extraction"
    STYLE_TRANSFER = "style_transfer"
    STYLE_APPLICATION = "style_transfer"
    RENDERING = "rendering"


class VideoFormat(str, Enum):
    """Supported video formats."""

    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    MKV = "mkv"
    WEBM = "webm"


ALLOWED_VIDEO_FORMATS = {fmt.value for fmt in VideoFormat}
ALLOWED_VIDEO_EXTENSIONS = {f".{fmt.value}" for fmt in VideoFormat}

# Job queue keys (Redis)
JOB_QUEUE_KEY = "clipzy:jobs:queue"
JOB_STATUS_PREFIX = "clipzy:job:"
JOB_RESULT_PREFIX = "clipzy:result:"
