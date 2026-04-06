"""Motion analysis using optical flow."""

import cv2
import numpy as np
from typing import TYPE_CHECKING
from app.core.logging_config import get_logger
from app.analysis.models import Motion

if TYPE_CHECKING:
    from app.analysis.video_ingestion import VideoIngestion

logger = get_logger(__name__)


class MotionAnalyzer:
    """Analyzes motion in video using optical flow."""

    def __init__(self, sample_rate: int = 4, batch_size: int = 400):
        """
        Initialize motion analyzer.

        Args:
            sample_rate: Analyze every Nth frame
            batch_size: Number of frames to load into memory at once
        """
        self.sample_rate = sample_rate
        self.batch_size = batch_size

    def analyze_motion_batched(self, video: "VideoIngestion", fps: float) -> list[Motion]:
        """
        Analyze motion across video frames using batched processing.
        
        Processes video in chunks to minimize memory usage.

        Args:
            video: VideoIngestion object for the video
            fps: Frames per second

        Returns:
            List of Motion objects with intensity over time
        """
        motion_data = []
        
        if video.total_frames < 2:
            logger.warning("Not enough frames for motion analysis")
            return []

        prev_gray = None
        frame_count = 0
        analyzed_count = 0

        # Reset to start
        video.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        while True:
            ret, frame = video.cap.read()
            if not ret:
                break

            if frame_count % self.sample_rate == 0:
                current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if prev_gray is not None:
                    try:
                        # Calculate optical flow
                        flow = cv2.calcOpticalFlowFarneback(
                            prev_gray, current_gray, None,
                            pyr_scale=0.5,
                            levels=3,
                            winsize=15,
                            iterations=3,
                            poly_n=5,
                            poly_sigma=1.1,
                            flags= 0
                        )

                        # Calculate magnitude and angle
                        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

                        # Average motion intensity
                        motion_intensity = float(np.mean(magnitude)) / 20.0  # Normalize
                        motion_intensity = min(motion_intensity, 1.0)  # Cap at 1.0

                        timestamp = (frame_count / self.sample_rate) / fps

                        motion = Motion(
                            timestamp=timestamp,
                            intensity=motion_intensity,
                        )
                        motion_data.append(motion)
                        analyzed_count += 1

                    except cv2.error as e:
                        logger.warning(f"Optical flow calculation failed at frame {frame_count}: {str(e)}")
                        # Continue with next frame on error

                prev_gray = current_gray

            frame_count += 1

            # Periodically log progress for long videos
            if frame_count % (self.batch_size * self.sample_rate) == 0:
                logger.info(f"Motion analysis progress: {frame_count}/{video.total_frames} frames processed")

        logger.info(
            f"Motion analysis complete",
            extra={
                "frames_analyzed": analyzed_count,
                "avg_intensity": np.mean([m.intensity for m in motion_data]) if motion_data else 0
            }
        )

        return motion_data

    def analyze_motion(self, frames: list[np.ndarray], fps: float) -> list[Motion]:
        """
        Analyze motion across frames using optical flow.

        Args:
            frames: List of video frames
            fps: Frames per second

        Returns:
            List of Motion objects with intensity over time
        """
        if len(frames) < 2:
            logger.warning("Not enough frames for motion analysis")
            return []

        motion_data = []

        # Convert first frame to grayscale
        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

        for i in range(1, len(frames), self.sample_rate):
            current_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)

            # Calculate optical flow (Lucas-Kanade)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, current_gray, None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.1,
                flags=0
            )

            # Calculate magnitude and angle
            magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

            # Average motion intensity
            motion_intensity = float(np.mean(magnitude)) / 20.0  # Normalize
            motion_intensity = min(motion_intensity, 1.0)  # Cap at 1.0

            timestamp = (i / self.sample_rate) / fps

            motion = Motion(
                timestamp=timestamp,
                intensity=motion_intensity,
            )
            motion_data.append(motion)

            prev_gray = current_gray

        logger.info(
            f"Motion analysis complete",
            extra={"frames_analyzed": len(motion_data), "avg_intensity": np.mean([m.intensity for m in motion_data])}
        )

        return motion_data
