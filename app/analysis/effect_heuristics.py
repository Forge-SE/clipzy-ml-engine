"""Heuristics for detecting editing effects."""

from typing import Optional

import numpy as np
from app.core.logging_config import get_logger
from app.analysis.models import (
    Beat, Cut, Effects, Motion, SpeechSegment
)

logger = get_logger(__name__)


class EffectHeuristics:
    """Detects editing effects using heuristics."""

    def __init__(
        self,
        motion_intensity_threshold: float = 0.15,
        jump_cut_threshold: float = 0.8
    ):
        """
        Initialize effect detector.

        Args:
            motion_intensity_threshold: Threshold for detecting motion
            jump_cut_threshold: Similarity threshold for jump cuts
        """
        self.motion_intensity_threshold = motion_intensity_threshold
        self.jump_cut_threshold = jump_cut_threshold

    def detect_effects(
        self,
        cuts: list[Cut],
        motion: list[Motion],
        beats: list[Beat],
        similarities: list[float],
        total_duration: float,
        avg_shot_duration: float,
    ) -> Effects:
        """
        Detect editing effects from analysis data.

        Args:
            cuts: Shot boundaries
            motion: Motion timeline
            beats: Audio beats
            similarities: Scene similarity scores
            total_duration: Total video duration
            avg_shot_duration: Average shot length

        Returns:
            Effects object with detected effects
        """
        # Jump cuts: high similarity between consecutive shots
        jump_cuts = len([s for s in similarities if s > self.jump_cut_threshold]) > (len(similarities) * 0.2)

        # Zoom frequency: estimate from motion intensity changes
        zoom_frequency = self._estimate_zoom_frequency(motion)

        # Beat sync: how often cuts align with beats
        beat_sync_score = self._compute_beat_sync(cuts, beats)

        # Fast pacing: avg shot duration < 2 seconds
        fast_pacing = avg_shot_duration < 2.0

        # Motion heavy: high average motion intensity
        motion_heavy = (
            np.mean([m.intensity for m in motion]) > self.motion_intensity_threshold * 2
            if motion
            else False
        )

        # Talking head: long continuous speech without cuts
        talking_head = False  # Would need speech analysis

        effects = Effects(
            has_jump_cuts=jump_cuts,
            zoom_frequency=zoom_frequency,
            beat_sync_score=beat_sync_score,
            fast_pacing=fast_pacing,
            motion_heavy=motion_heavy,
            talking_head=talking_head,
            scene_cuts_count=len(cuts),
        )

        logger.info(
            f"Effect detection complete",
            extra={
                "jump_cuts": jump_cuts,
                "fast_pacing": fast_pacing,
                "motion_heavy": motion_heavy,
                "beat_sync": beat_sync_score,
            }
        )

        return effects

    def _estimate_zoom_frequency(self, motion: list[Motion]) -> float:
        """Estimate zoom frequency from motion intensity spikes."""
        if not motion:
            return 0.0

        # Detect spikes in motion (potential zooms)
        intensities = [m.intensity for m in motion]
        threshold = np.mean(intensities) + np.std(intensities)

        spikes = sum(1 for i in intensities if i > threshold)
        zoom_frequency = spikes / len(motion) if motion else 0.0

        return min(zoom_frequency, 1.0)

    def _compute_beat_sync(self, cuts: list[Cut], beats: list[Beat]) -> float:
        """
        Compute how well cuts align with beats.

        Args:
            cuts: Shot cuts
            beats: Audio beats

        Returns:
            Sync score 0-1
        """
        if not cuts or not beats:
            return 0.0

        beat_times = set(b.timestamp for b in beats)
        tolerance = 0.1  # 100ms tolerance

        synced_cuts = 0
        for cut in cuts:
            # Check if cut is near any beat
            nearby_beats = [b for b in beats if abs(b.timestamp - cut.timestamp) < tolerance]
            if nearby_beats:
                synced_cuts += 1

        sync_score = synced_cuts / len(cuts) if cuts else 0.0
        return float(sync_score)
