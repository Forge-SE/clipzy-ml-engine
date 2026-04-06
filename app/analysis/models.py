"""Data models for video analysis output."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np


@dataclass
class Cut:
    """Information about a cut in the video."""

    timestamp: float  # seconds
    confidence: float  # 0-1
    shot_duration: float  # Duration until next cut


@dataclass
class Motion:
    """Motion information."""

    timestamp: float
    intensity: float  # 0-1
    direction: Optional[str] = None  # horizontal, vertical, etc.


@dataclass
class Beat:
    """Audio beat information."""

    timestamp: float  # seconds
    confidence: float  # 0-1


@dataclass
class SpeechSegment:
    """Speech segment with text and timestamps."""

    start: float
    end: float
    text: str
    confidence: float = 0.95


@dataclass
class Pacing:
    """Pacing information."""

    avg_shot_duration: float
    variance: float
    type: str  # fast, medium, slow
    total_shots: int


@dataclass
class Audio:
    """Audio analysis results."""

    bpm: Optional[float] = None
    beats: list[Beat] = field(default_factory=list)
    dominant_frequency: Optional[float] = None
    energy: Optional[float] = None


@dataclass
class Speech:
    """Speech analysis results."""

    transcript: str
    segments: list[SpeechSegment] = field(default_factory=list)
    has_speech: bool = True
    speech_percentage: float = 0.0


@dataclass
class Visual:
    """Visual analysis results."""

    embeddings: list[np.ndarray] = field(default_factory=list)
    embedding_timestamps: list[float] = field(default_factory=list)
    scene_similarity: list[float] = field(default_factory=list)
    avg_brightness: Optional[float] = None
    avg_contrast: Optional[float] = None


@dataclass
class Color:
    """Color analysis results."""

    brightness: float  # 0-1
    contrast: float  # 0-1
    saturation: float  # 0-1
    dominant_colors: list[tuple[int, int, int]] = field(default_factory=list)  # RGB
    dominant_color_names: list[str] = field(default_factory=list)
    color_temperature: str = "neutral"  # warm, neutral, cool


@dataclass
class Effects:
    """Detected or inferred effects."""

    has_jump_cuts: bool = False
    zoom_frequency: float = 0.0
    beat_sync_score: float = 0.0  # 0-1, how well cuts align with beats
    fast_pacing: bool = False
    motion_heavy: bool = False
    talking_head: bool = False
    scene_cuts_count: int = 0


@dataclass
class StyleDNA:
    """Complete style DNA extracted from a video."""

    # Metadata
    video_path: str
    duration: float  # Total video duration in seconds
    fps: float
    resolution: tuple[int, int]  # width, height
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Analysis components
    cuts: list[Cut] = field(default_factory=list)
    pacing: Optional[Pacing] = None
    motion: list[Motion] = field(default_factory=list)
    audio: Audio = field(default_factory=Audio)
    speech: Speech = field(default_factory=Speech)
    visual: Visual = field(default_factory=Visual)
    color: Color = field(default_factory=Color)
    effects: Effects = field(default_factory=Effects)

    # Confidence
    overall_confidence: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": {
                "video_path": self.video_path,
                "duration": self.duration,
                "fps": self.fps,
                "resolution": self.resolution,
                "created_at": self.created_at.isoformat(),
            },
            "cuts": [
                {
                    "timestamp": c.timestamp,
                    "confidence": c.confidence,
                    "shot_duration": c.shot_duration,
                }
                for c in self.cuts
            ],
            "pacing": (
                {
                    "avg_shot_duration": self.pacing.avg_shot_duration,
                    "variance": self.pacing.variance,
                    "type": self.pacing.type,
                    "total_shots": self.pacing.total_shots,
                }
                if self.pacing
                else None
            ),
            "motion": {
                "timeline": [
                    {"timestamp": m.timestamp, "intensity": m.intensity}
                    for m in self.motion
                ],
                "peaks": [m for m in self.motion if m.intensity > 0.7],
            },
            "audio": {
                "bpm": self.audio.bpm,
                "beats": [{"timestamp": b.timestamp, "confidence": b.confidence} for b in self.audio.beats],
                "dominant_frequency": self.audio.dominant_frequency,
                "energy": self.audio.energy,
            },
            "speech": {
                "transcript": self.speech.transcript,
                "segments": [
                    {
                        "start": s.start,
                        "end": s.end,
                        "text": s.text,
                        "confidence": s.confidence,
                    }
                    for s in self.speech.segments
                ],
                "has_speech": self.speech.has_speech,
                "speech_percentage": self.speech.speech_percentage,
            },
            "visual": {
                "embedding_timestamps": self.visual.embedding_timestamps,
                "avg_brightness": self.visual.avg_brightness,
                "avg_contrast": self.visual.avg_contrast,
                "scene_similarity_average": (
                    sum(self.visual.scene_similarity) / len(self.visual.scene_similarity)
                    if self.visual.scene_similarity
                    else 0.0
                ),
            },
            "color": {
                "brightness": self.color.brightness,
                "contrast": self.color.contrast,
                "saturation": self.color.saturation,
                "dominant_color_names": self.color.dominant_color_names,
                "color_temperature": self.color.color_temperature,
            },
            "effects": {
                "has_jump_cuts": self.effects.has_jump_cuts,
                "zoom_frequency": self.effects.zoom_frequency,
                "beat_sync_score": self.effects.beat_sync_score,
                "fast_pacing": self.effects.fast_pacing,
                "motion_heavy": self.effects.motion_heavy,
                "talking_head": self.effects.talking_head,
                "scene_cuts_count": self.effects.scene_cuts_count,
            },
            "overall_confidence": self.overall_confidence,
        }
