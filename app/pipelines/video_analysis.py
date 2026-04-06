"""Video analysis pipeline."""

from typing import Any

from app.core.logging_config import get_logger
from app.analysis.pipeline import VideoAnalysisPipeline
from app.analysis.config import AnalysisConfig

logger = get_logger(__name__)


class VideoAnalyzer:
    """Analyzes video content: cuts, pacing, composition, etc."""

    @staticmethod
    def analyze(video_path: str, config: AnalysisConfig = None) -> dict[str, Any]:
        """
        Analyze video for cuts, pacing, motion, composition.

        Uses the full video analysis engine with OpenCV, PySceneDetect, Librosa,
        Whisper, and CLIP to extract comprehensive style DNA.

        Args:
            video_path: Path to video file
            config: Optional analysis configuration

        Returns:
            Dictionary with complete analysis results
        """
        logger.info(f"Starting video analysis", extra={"video_path": video_path})

        try:
            # Use the video analysis pipeline
            pipeline = VideoAnalysisPipeline(config=config)
            style_dna = pipeline.analyze(video_path)

            # Convert StyleDNA to dictionary format for compatibility
            analysis = {
                "shots": [
                    {
                        "id": i,
                        "timestamp": cut.timestamp,
                        "confidence": cut.confidence,
                        "shot_duration": cut.shot_duration,
                    }
                    for i, cut in enumerate(style_dna.cuts)
                ],
                "shot_count": len(style_dna.cuts),
                "average_shot_length": (
                    style_dna.pacing.avg_shot_duration
                    if style_dna.pacing
                    else 0.0
                ),
                "pacing_type": style_dna.pacing.type if style_dna.pacing else "unknown",
                "cut_frequency": (
                    len(style_dna.cuts) / (style_dna.duration / 60)
                    if style_dna.duration > 0
                    else 0
                ),
                "style_dna": style_dna.to_dict(),
            }

            logger.info(
                f"Video analysis complete",
                extra={
                    "video_path": video_path,
                    "shots": len(style_dna.cuts),
                    "confidence": style_dna.overall_confidence,
                }
            )
            
            # Cleanup temporary files
            pipeline.cleanup()
            
            return analysis

        except Exception as e:
            logger.error(
                f"Video analysis failed: {str(e)}",
                extra={"video_path": video_path}
            )
            raise
