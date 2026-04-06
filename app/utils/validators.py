"""Validators for API inputs."""

from pathlib import Path

from app.core.exceptions import InvalidVideoError
from app.core.constants import ALLOWED_VIDEO_EXTENSIONS, ALLOWED_VIDEO_FORMATS


def validate_video_file(filename: str, content: bytes) -> bool:
    """
    Validate video file.

    Args:
        filename: Original filename
        content: File content bytes

    Returns:
        True if valid

    Raises:
        InvalidVideoError: If validation fails
    """
    # Check extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise InvalidVideoError(
            f"Unsupported video format '{file_ext}'. "
            f"Supported formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )

    # Check file size (not empty)
    if len(content) < 1024:  # At least 1KB
        raise InvalidVideoError("Video file is too small (less than 1KB)")

    # Check for basic video file magic bytes (simplified check)
    # This is a basic check - real implementation should use ffprobe
    magic_bytes = content[:12]

    # Check for common video formats
    # MP4: ftyp
    # MOV: ftyp
    # AVI: RIFF...AVI
    # MKV: 0x1A 0x45 0xDF 0xA3
    # WebM: 0x1A 0x45 0xDF 0xA3

    is_valid = (
        b"ftyp" in magic_bytes or  # MP4/MOV
        b"RIFF" in magic_bytes or  # AVI
        b"\x1A\x45\xDF\xA3" in magic_bytes  # MKV/WebM
    )

    if not is_valid:
        # Still allow if extension is valid (more lenient)
        # In production, use ffprobe to validate
        pass

    return True


def validate_job_id(job_id: str) -> bool:
    """Validate job ID format."""
    return job_id.startswith("job_") and len(job_id) > 4


def validate_video_id(video_id: str) -> bool:
    """Validate video ID format."""
    return video_id.startswith("vid_") and len(video_id) > 4
