"""Shot detection using PySceneDetect."""

from typing import Optional

from scenedetect import detect, ContentDetector
from app.core.logging_config import get_logger
from app.analysis.models import Cut

logger = get_logger(__name__)


class ShotDetector:
    """Detects shot boundaries in video."""

    def __init__(self, threshold: float = 24.0):
        """
        Initialize shot detector.

        Args:
            threshold: ContentDetector threshold (higher = fewer cuts)
        """
        self.threshold = threshold

    def detect_cuts(self, video_path: str) -> list[Cut]:
        """
        Detect shot cuts in video.

        Args:
            video_path: Path to video file

        Returns:
            List of Cut objects
        """
        try:
            # Detect scenes using ContentDetector
            scenes = detect(video_path, ContentDetector(threshold=self.threshold))

            cuts = []
            for i, scene in enumerate(scenes):
                timestamp = scene[0].get_seconds()

                # Calculate shot duration (time until next cut)
                if i < len(scenes) - 1:
                    next_timestamp = scenes[i + 1][0].get_seconds()
                    shot_duration = next_timestamp - timestamp
                else:
                    shot_duration = 0.0  # Last shot

                cut = Cut(
                    timestamp=timestamp,
                    confidence=0.95,  # PySceneDetect is fairly confident
                    shot_duration=shot_duration,
                )
                cuts.append(cut)

            logger.info(
                f"Shot detection complete",
                extra={"cuts": len(cuts), "threshold": self.threshold}
            )
            return cuts

        except Exception as e:
            logger.error(f"Shot detection failed: {str(e)}")
            raise
