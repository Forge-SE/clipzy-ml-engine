
from typing import Optional

import cv2
import numpy as np
from app.core.logging_config import get_logger
from app.analysis.models import Color

logger = get_logger(__name__)


class ColorAnalyzer:
    """Analyzes color properties in video."""

    def __init__(self):
       
        self.color_names = {
            (0, 0, 0): "Black",
            (255, 255, 255): "White",
            (255, 0, 0): "Red",
            (0, 255, 0): "Green",
            (0, 0, 255): "Blue",
            (255, 255, 0): "Yellow",
            (255, 0, 255): "Magenta",
            (0, 255, 255): "Cyan",
        }

    def analyze_frames(self, frames: list[np.ndarray], sample_rate: int = 5) -> Color:
        """
        Analyze color properties across frames.

        Args:
            frames: List of frames (BGR)
            sample_rate: Analyze every Nth frame

        Returns:
            Color object with statistics
        """
        if not frames:
            return Color()

        brightnesses = []
        contrasts = []
        saturations = []
        all_dominant_colors = []

        logger.info(f"Analyzing colors for {len(frames)} frames")

        for i in range(0, len(frames), sample_rate):
            frame = frames[i]

            # Convert BGR to HSV for saturation
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Brightness (V in HSV)
            brightness = np.mean(hsv[:, :, 2]) / 255.0
            brightnesses.append(brightness)

            # Saturation (S in HSV)
            saturation = np.mean(hsv[:, :, 1]) / 255.0
            saturations.append(saturation)

            # Contrast (std of luminance)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            contrast = np.std(gray) / 255.0
            contrasts.append(contrast)

            # Dominant colors (k-means clustering)
            dominant = self._get_dominant_colors(frame, k=3)
            all_dominant_colors.extend(dominant)

        # Calculate averages
        avg_brightness = float(np.mean(brightnesses)) if brightnesses else 0.5
        avg_contrast = float(np.mean(contrasts)) if contrasts else 0.5
        avg_saturation = float(np.mean(saturations)) if saturations else 0.5

        # Most common dominant colors
        color_counts = {}
        for color in all_dominant_colors:
            color_tuple = tuple(color)
            color_counts[color_tuple] = color_counts.get(color_tuple, 0) + 1

        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        dominant_colors = [color for color, count in sorted_colors[:5]]
        dominant_color_names = [self._name_color(color) for color in dominant_colors]

        # Color temperature
        color_temp = self._estimate_color_temperature(avg_brightness, dominant_colors)

        color = Color(
            brightness=avg_brightness,
            contrast=avg_contrast,
            saturation=avg_saturation,
            dominant_colors=dominant_colors,
            dominant_color_names=dominant_color_names,
            color_temperature=color_temp,
        )

        logger.info(
            f"Color analysis complete",
            extra={
                "brightness": avg_brightness,
                "contrast": avg_contrast,
                "saturation": avg_saturation,
            }
        )

        return color

    def _get_dominant_colors(self, frame: np.ndarray, k: int = 3) -> list[tuple[int, int, int]]:
        """Extract dominant colors using k-means."""
        # Reshape frame
        pixel_values = frame.reshape((-1, 3))
        pixel_values = np.float32(pixel_values)

        # K-means
        _, _, centers = cv2.kmeans(
            pixel_values,
            k,
            None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2),
            10,
            cv2.KMEANS_INIT_WITH_PP_CENTERS,
        )

        return [tuple(int(c) for c in center) for center in centers]

    def _name_color(self, bgr_color: tuple) -> str:
        """Name a color (BGR tuple)."""
        # Simple nearest-neighbor color naming
        min_dist = float('inf')
        closest_name = "Unknown"

        for known_color, name in self.color_names.items():
            dist = sum((a - b) ** 2 for a, b in zip(bgr_color, known_color)) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest_name = name

        return closest_name

    def _estimate_color_temperature(self, brightness: float, colors: list[tuple]) -> str:
        """Estimate color temperature from brightness and dominant colors."""
        if brightness > 0.7:
            return "bright"
        elif brightness < 0.3:
            return "dark"
        else:
            return "neutral"
