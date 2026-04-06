"""Style JSON schema definition."""

from typing import Optional

from pydantic import BaseModel, Field


class ColorGrade(BaseModel):
    """Color grading information."""

    temperature: float = Field(..., description="Color temperature (-100 to 100)")
    tint: float = Field(..., description="Color tint (-100 to 100)")
    saturation: float = Field(..., description="Saturation (-100 to 100)")
    contrast: float = Field(..., description="Contrast (-100 to 100)")
    highlights: float = Field(..., description="Highlight adjustment (-100 to 100)")
    shadows: float = Field(..., description="Shadow adjustment (-100 to 100)")


class AudioStyle(BaseModel):
    """Audio processing information."""

    normalization_level: float = Field(..., description="Normalized audio level (0-1)")
    compression_ratio: float = Field(..., description="Audio compression ratio")
    bass_boost: float = Field(..., description="Bass boost amount (0-100)")
    enhance_speech: bool = Field(..., description="Enable speech enhancement")


class TransitionStyle(BaseModel):
    """Transition effects information."""

    type: str = Field(..., description="Transition type (cut, fade, wipe, etc.)")
    duration_ms: int = Field(..., description="Transition duration in milliseconds")
    easing: str = Field(..., description="Easing function (linear, ease-in, ease-out, etc.)")


class TextOverlay(BaseModel):
    """Text overlay information."""

    content: str = Field(..., description="Text content")
    font: str = Field(..., description="Font family")
    size: int = Field(..., description="Font size in pixels")
    color: str = Field(..., description="Color as hex code")
    position: str = Field(..., description="Position (top-left, center, bottom-right, etc.)")
    duration_ms: Optional[int] = Field(None, description="Duration to display text")


class DetectedBeat(BaseModel):
    """Musical beat information."""

    timestamp_ms: float = Field(..., description="Beat timestamp in milliseconds")
    confidence: float = Field(..., description="Confidence score (0-1)")
    frequency: str = Field(..., description="Frequency band (bass, mid, treble)")


class StyleJSON(BaseModel):
    """
    Complete style manifesto for video processing.

    This describes the visual and audio style extracted from a template video
    or specified by the user, to be applied to user footage.
    """

    version: str = Field(default="1.0", description="Style schema version")

    # Color & Visual Style
    color_grade: ColorGrade = Field(..., description="Color grading preferences")
    aspect_ratio: str = Field(..., description="Target aspect ratio (16:9, 9:16, 1:1, etc.)")
    frame_rate: int = Field(..., description="Target frame rate (24, 30, 60 fps)")

    # Audio Style
    audio_style: AudioStyle = Field(..., description="Audio processing preferences")

    # Pacing & Motion
    cut_frequency: float = Field(
        ...,
        description="Average cuts per minute"
    )
    motion_intensity: float = Field(
        ...,
        ge=0, le=100,
        description="Overall motion intensity (0-100)"
    )
    zoom_usage: float = Field(
        ...,
        ge=0, le=100,
        description="Zoom/pan usage frequency (0-100)"
    )

    # Transitions
    primary_transition: TransitionStyle = Field(..., description="Primary transition style")
    secondary_transition: Optional[TransitionStyle] = Field(None, description="Secondary transition style")

    # Text & Graphics
    text_overlays: list[TextOverlay] = Field(default_factory=list, description="Text overlay styles")
    use_subtitles: bool = Field(default=False, description="Include subtitles/captions")

    # Music/Beat Sync
    detected_beats: list[DetectedBeat] = Field(default_factory=list, description="Detected musical beats")
    tempo_bpm: Optional[float] = Field(None, description="Overall tempo in BPM")
    music_genre: Optional[str] = Field(None, description="Detected music genre")

    # Metadata
    created_at: str = Field(..., description="ISO timestamp of creation")
    source_duration_seconds: float = Field(..., description="Duration of source video")
    extraction_confidence: float = Field(
        ...,
        ge=0, le=1,
        description="Confidence of extraction (0-1)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "version": "1.0",
                "color_grade": {
                    "temperature": 10,
                    "tint": 5,
                    "saturation": 20,
                    "contrast": 15,
                    "highlights": 10,
                    "shadows": -5,
                },
                "aspect_ratio": "16:9",
                "frame_rate": 30,
                "audio_style": {
                    "normalization_level": 0.85,
                    "compression_ratio": 4.0,
                    "bass_boost": 20,
                    "enhance_speech": True,
                },
                "cut_frequency": 3.5,
                "motion_intensity": 65,
                "zoom_usage": 30,
                "primary_transition": {
                    "type": "fade",
                    "duration_ms": 300,
                    "easing": "ease-in-out",
                },
                "detected_beats": [
                    {
                        "timestamp_ms": 1000,
                        "confidence": 0.95,
                        "frequency": "bass",
                    }
                ],
                "tempo_bpm": 120.0,
                "music_genre": "pop",
                "created_at": "2024-04-05T10:30:00Z",
                "source_duration_seconds": 60.0,
                "extraction_confidence": 0.92,
            }
        }
