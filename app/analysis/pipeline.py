"""Main video analysis pipeline orchestration."""

from pathlib import Path
from app.core.logging_config import get_logger
from app.analysis.config import AnalysisConfig
from app.analysis.models import StyleDNA
from app.analysis.video_ingestion import VideoIngestion
from app.analysis.shot_detection import ShotDetector
from app.analysis.motion_analysis import MotionAnalyzer
from app.analysis.audio_analysis import AudioAnalyzer
from app.analysis.speech_recognition import SpeechRecognizer
from app.analysis.visual_embeddings import VisualEmbedder
from app.analysis.color_analysis import ColorAnalyzer
from app.analysis.pacing_analyzer import PacingAnalyzer
from app.analysis.effect_heuristics import EffectHeuristics
from app.analysis.style_aggregator import StyleAggregator
from app.utils.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class VideoAnalysisPipeline:
    """Main pipeline for analyzing video and extracting style DNA."""

    def __init__(self, config: AnalysisConfig = None, progress_tracker: ProgressTracker = None):
        """
        Initialize pipeline.

        Args:
            config: Analysis configuration
            progress_tracker: Optional progress tracker for detailed output
        """
        self.config = config or AnalysisConfig()
        self.config.ensure_temp_dir()
        self.progress_tracker = progress_tracker

        logger.info("VideoAnalysisPipeline initialized")

    def analyze(self, video_path: str) -> StyleDNA:
        """
        Run complete video analysis pipeline.

        Args:
            video_path: Path to video file

        Returns:
            StyleDNA object with complete analysis
        """
        logger.info(f"Starting video analysis", extra={"video": video_path})

        # Step 1: Video Ingestion
        logger.info("Step 1/8: Video Ingestion")
        video = VideoIngestion(video_path)
        video_info = video.get_video_info()

        # Step 2: Shot Detection
        logger.info("Step 2/8: Shot Detection")
        shot_detector = ShotDetector(threshold=self.config.threshold)
        cuts = shot_detector.detect_cuts(video_path)

        # Step 3: Extract frames for visual analysis only (not for motion - uses batched processing)
        logger.info("Step 3/8: Extracting Frames for Visual Analysis")
        # Use higher sample rate to reduce memory: extract every 4th frame instead of every 2nd
        visual_sample_rate = max(4, self.config.frame_sample_rate * 2)
        frames = video.extract_frames(sample_rate=visual_sample_rate)
        logger.info(f"Extracted {len(frames)} frames for visual analysis (sample rate: {visual_sample_rate})")

        # Step 4: Motion Analysis (using batched processing to minimize memory)
        logger.info("Step 4/8: Motion Analysis")
        motion_analyzer = MotionAnalyzer(sample_rate=self.config.motion_sample_rate)
        motion = motion_analyzer.analyze_motion_batched(video, video_info["fps"])

        # Step 5: Extract Audio
        logger.info("Step 5/8: Audio Extraction")
        audio_path = video.extract_audio(str(self.config.temp_dir / "audio.wav"))

        # Step 6: Audio Analysis
        logger.info("Step 6/8: Audio Analysis")
        if audio_path:
            audio_analyzer = AudioAnalyzer(sample_rate=self.config.sample_rate)
            audio = audio_analyzer.analyze_audio(audio_path)
        else:
            logger.warning("Skipping audio analysis (FFmpeg not available)")
            audio = None

        # Step 7: Speech Recognition
        logger.info("Step 7/8: Speech Recognition")
        speech = None
        if audio_path:
            try:
                speech_recognizer = SpeechRecognizer(
                    model_name=self.config.whisper_model,
                    device=self.config.device,
                    fp16=self.config.whisper_fp16,
                )
                speech = speech_recognizer.recognize_speech(audio_path)
            except Exception as e:
                logger.warning(f"Speech recognition failed: {str(e)}")
                speech = None
        else:
            logger.warning("Skipping speech recognition (no audio available)")

        # Step 8: Visual Embeddings & Color Analysis
        logger.info("Step 8/8: Visual Analysis (CLIP + Color)")
        embedder = VisualEmbedder(
            model_name=self.config.clip_model_name,
            device=self.config.device,
        )
        embeddings, timestamps = embedder.embed_frames(
            frames,
            sample_rate=self.config.extract_every_n_frames
        )

        similarities = embedder.compute_similarity_sequence(embeddings)

        color_analyzer = ColorAnalyzer()
        color = color_analyzer.analyze_frames(frames, sample_rate=self.config.color_sample_rate)

        # Pacing Analysis
        logger.info("Computing Pacing")
        pacing_analyzer = PacingAnalyzer()
        pacing = pacing_analyzer.analyze_pacing(cuts)

        # Effect Detection
        logger.info("Detecting Effects")
        effect_detector = EffectHeuristics(
            motion_intensity_threshold=self.config.motion_intensity_threshold,
            jump_cut_threshold=self.config.jump_cut_threshold,
        )
        effects = effect_detector.detect_effects(
            cuts=cuts,
            motion=motion,
            beats=audio.beats,
            similarities=similarities,
            total_duration=video_info["duration"],
            avg_shot_duration=pacing.avg_shot_duration if pacing else 0.0,
        )

        # Create Visual object
        from app.analysis.models import Visual
        visual = Visual(
            embeddings=embeddings,
            embedding_timestamps=timestamps,
            scene_similarity=similarities,
        )

        # Aggregation
        logger.info("Aggregating Results")
        aggregator = StyleAggregator()
        style_dna = aggregator.aggregate(
            video_path=video_path,
            duration=video_info["duration"],
            fps=video_info["fps"],
            resolution=video_info["resolution"],
            cuts=cuts,
            pacing=pacing,
            motion=motion,
            audio=audio,
            speech=speech or Speech(),
            visual=visual,
            color=color,
            effects=effects,
        )

        logger.info(
            f"Video analysis complete",
            extra={"confidence": style_dna.overall_confidence}
        )

        return style_dna

    def cleanup(self) -> None:
        """Clean up temporary files."""
        self.config.cleanup_temp()
        logger.info("Cleanup complete")


# Import at end to avoid circular imports
from app.analysis.models import Speech
