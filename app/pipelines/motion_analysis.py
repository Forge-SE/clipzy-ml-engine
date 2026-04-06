"""Motion analysis pipeline."""

from typing import Any

from app.core.logging_config import get_logger
from app.analysis.video_ingestion import VideoIngestion
from app.analysis.motion_analysis import MotionAnalyzer as OpticalFlowAnalyzer
from app.analysis.config import AnalysisConfig

logger = get_logger(__name__)


class MotionAnalyzer:
    """Analyzes motion in video: camera movement, object motion, dynamics."""

    @staticmethod
    def analyze(video_path: str, config: AnalysisConfig = None) -> dict[str, Any]:
        """
        Analyze motion in video using optical flow.

        Uses OpenCV Farneback optical flow to detect camera movement and
        object motion throughout the video.

        Args:
            video_path: Path to video file
            config: Optional analysis configuration

        Returns:
            Dictionary with motion analysis results
        """
        logger.info(f"Starting motion analysis", extra={"video_path": video_path})

        config = config or AnalysisConfig()

        try:
            # Load video
            video = VideoIngestion(video_path)
            fps = video.fps

            # Analyze motion using batched processing to minimize memory usage
            motion_analyzer = OpticalFlowAnalyzer(sample_rate=config.motion_sample_rate)
            motion_timeline = motion_analyzer.analyze_motion_batched(video, fps)

            # Calculate statistics
            if motion_timeline:
                intensities = [m.intensity for m in motion_timeline]
                avg_intensity = sum(intensities) / len(intensities)
                max_intensity = max(intensities)
                motion_spikes = sum(1 for i in intensities if i > avg_intensity * 1.5)
            else:
                avg_intensity = 0.0
                max_intensity = 0.0
                motion_spikes = 0

            analysis = {
                "average_intensity": avg_intensity,
                "max_intensity": max_intensity,
                "motion_spikes": motion_spikes,
                "motion_timeline": [
                    {
                        "timestamp": m.timestamp,
                        "intensity": m.intensity,
                    }
                    for m in motion_timeline
                ],
                "has_rapid_motion": max_intensity > 0.7,
                "has_static_sections": min((i for i in [m.intensity for m in motion_timeline]), default=0) < 0.1,
            }

            logger.info(
                f"Motion analysis complete",
                extra={
                    "video_path": video_path,
                    "avg_intensity": avg_intensity,
                    "motion_events": len(motion_timeline),
                }
            )

            return analysis

        except Exception as e:
            logger.error(
                f"Motion analysis failed: {str(e)}",
                extra={"video_path": video_path}
            )
            raise
