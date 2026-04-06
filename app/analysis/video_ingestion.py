"""Video and audio ingestion module."""

import subprocess
import shutil
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and available."""
    return shutil.which("ffmpeg") is not None


class VideoIngestion:
    """Handles video loading and processing."""

    def __init__(self, video_path: str):
        """Initialize video ingestion."""
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

        logger.info(
            f"Video loaded",
            extra={
                "path": str(self.video_path),
                "fps": self.fps,
                "frames": self.total_frames,
                "duration": self.duration,
                "resolution": f"{self.width}x{self.height}",
            }
        )

    def get_frame(self, frame_number: int) -> Optional[np.ndarray]:
        """Get a specific frame by number."""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        return frame if ret else None

    def get_frame_at_time(self, timestamp: float) -> Optional[np.ndarray]:
        """Get frame at specific timestamp (seconds)."""
        frame_number = int(timestamp * self.fps)
        return self.get_frame(min(frame_number, self.total_frames - 1))

    def extract_frames(self, sample_rate: int = 1) -> list[np.ndarray]:
        """
        Extract frames at specified sample rate.

        Args:
            sample_rate: Extract every Nth frame

        Returns:
            List of frames
        """
        frames = []
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        frame_count = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            if frame_count % sample_rate == 0:
                frames.append(frame)

            frame_count += 1

        logger.info(f"Extracted {len(frames)} frames at sample rate {sample_rate}")
        return frames

    def extract_audio(self, output_path: str = "./tmp_audio.wav") -> Optional[str]:
        """
        Extract audio from video using FFmpeg.

        Args:
            output_path: Path to save audio

        Returns:
            Path to extracted audio file, or None if FFmpeg is not available
        """
        # Check if FFmpeg is installed
        if not check_ffmpeg_installed():
            logger.warning(
                "FFmpeg is not installed. Audio analysis will be skipped.\n"
                "To install FFmpeg:\n"
                "  Windows: choco install ffmpeg (or download from https://ffmpeg.org/download.html)\n"
                "  macOS: brew install ffmpeg\n"
                "  Linux: sudo apt install ffmpeg"
            )
            return None

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                "ffmpeg",
                "-i", str(self.video_path),
                "-q:a", "9",  # Quality
                "-n",  # Don't overwrite
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0 and "File exists" not in result.stderr:
                raise RuntimeError(f"FFmpeg error: {result.stderr}")

            logger.info(f"Audio extracted to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to extract audio: {str(e)}")
            return None

    def get_video_info(self) -> dict:
        """Get video metadata."""
        return {
            "path": str(self.video_path),
            "fps": self.fps,
            "total_frames": self.total_frames,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "resolution": (self.width, self.height),
        }

    def __del__(self):
        """Clean up video capture."""
        if hasattr(self, 'cap'):
            self.cap.release()
