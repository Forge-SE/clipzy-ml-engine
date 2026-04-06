"""Aggregates analysis results into Style DNA."""

import numpy as np
from app.core.logging_config import get_logger
from app.analysis.models import (
    StyleDNA, Cut, Motion, Audio, Speech, Visual, Color, Effects, Pacing
)

logger = get_logger(__name__)


class StyleAggregator:
    """Aggregates individual analysis components into complete Style DNA."""

    def aggregate(
        self,
        video_path: str,
        duration: float,
        fps: float,
        resolution: tuple[int, int],
        cuts: list[Cut],
        pacing: Pacing,
        motion: list[Motion],
        audio: Audio,
        speech: Speech,
        visual: Visual,
        color: Color,
        effects: Effects,
    ) -> StyleDNA:
        """
        Aggregate all analysis results into Style DNA.

        Args:
            All individual analysis results

        Returns:
            Complete StyleDNA object
        """
        # Compute overall confidence based on available data
        confidence_scores = []

        if cuts:
            confidence_scores.append(0.95)  # Shot detection is reliable
        if motion:
            confidence_scores.append(0.90)  # Motion detection is reliable
        if audio.bpm:
            confidence_scores.append(0.85)  # BPM detection is fairly reliable
        if speech.has_speech:
            confidence_scores.append(0.90)  # Whisper is very accurate
        if visual.embedding_timestamps:
            confidence_scores.append(0.88)  # CLIP embeddings are good
        if color.brightness > 0:
            confidence_scores.append(0.95)  # Color analysis is deterministic

        overall_confidence = float(np.mean(confidence_scores)) if confidence_scores else 0.0

        style_dna = StyleDNA(
            video_path=video_path,
            duration=duration,
            fps=fps,
            resolution=resolution,
            cuts=cuts,
            pacing=pacing,
            motion=motion,
            audio=audio,
            speech=speech,
            visual=visual,
            color=color,
            effects=effects,
            overall_confidence=overall_confidence,
        )

        logger.info(
            f"Style DNA aggregated",
            extra={
                "cuts": len(cuts),
                "motion_points": len(motion),
                "beats": len(audio.beats),
                "speech_segments": len(speech.segments),
                "confidence": overall_confidence,
            }
        )

        return style_dna
