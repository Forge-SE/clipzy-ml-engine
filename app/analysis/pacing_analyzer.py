"""Pacing analysis from shot cuts."""

import numpy as np
from app.core.logging_config import get_logger
from app.analysis.models import Cut, Pacing

logger = get_logger(__name__)


class PacingAnalyzer:
    """Analyzes pacing from shot cuts."""

    def analyze_pacing(self, cuts: list[Cut]) -> Pacing:
        """
        Analyze pacing from shot boundaries.

        Args:
            cuts: List of shot cuts

        Returns:
            Pacing object
        """
        if not cuts or len(cuts) < 2:
            return Pacing(
                avg_shot_duration=0.0,
                variance=0.0,
                type="unknown",
                total_shots=len(cuts)
            )

        # Calculate shot durations
        durations = [cut.shot_duration for cut in cuts if cut.shot_duration > 0]

        if not durations:
            return Pacing(
                avg_shot_duration=0.0,
                variance=0.0,
                type="unknown",
                total_shots=len(cuts)
            )

        avg_duration = float(np.mean(durations))
        variance = float(np.var(durations))

        # Determine pacing type
        if avg_duration < 2.0:
            pacing_type = "fast"
        elif avg_duration < 4.0:
            pacing_type = "medium"
        else:
            pacing_type = "slow"

        pacing = Pacing(
            avg_shot_duration=avg_duration,
            variance=variance,
            type=pacing_type,
            total_shots=len(cuts)
        )

        logger.info(
            f"Pacing analysis complete",
            extra={
                "avg_duration": avg_duration,
                "type": pacing_type,
                "total_shots": len(cuts),
            }
        )

        return pacing
