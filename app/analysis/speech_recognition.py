"""Speech recognition using OpenAI Whisper."""

from typing import Optional

import whisper
from app.core.logging_config import get_logger
from app.analysis.models import Speech, SpeechSegment

logger = get_logger(__name__)


class SpeechRecognizer:
    """Recognizes speech using OpenAI Whisper."""

    def __init__(self, model_name: str = "base", device: str = "cpu", fp16: bool = True):
        """
        Initialize speech recognizer.

        Args:
            model_name: Whisper model size (tiny, small, base, medium, large)
            device: Device to run on (cpu or cuda)
            fp16: Use fp16 (only on CUDA)
        """
        self.model_name = model_name
        self.device = device
        self.fp16 = fp16 and device == "cuda"

        logger.info(f"Loading Whisper model: {model_name}")
        self.model = whisper.load_model(model_name, device=device)

    def recognize_speech(self, audio_path: str) -> Speech:
        """
        Recognize speech in audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Speech object with transcript and segments
        """
        try:
            logger.info(f"Recognizing speech", extra={"audio": audio_path})

            # Transcribe
            result = self.model.transcribe(audio_path, fp16=self.fp16, language="en")

            # Extract full transcript
            transcript = result.get("text", "").strip()

            # Extract segments with timestamps
            segments = []
            for segment in result.get("segments", []):
                speech_segment = SpeechSegment(
                    start=float(segment["start"]),
                    end=float(segment["end"]),
                    text=segment["text"].strip(),
                    confidence=0.95,  # Whisper doesn't provide segment confidence
                )
                segments.append(speech_segment)

            has_speech = len(transcript) > 0

            speech = Speech(
                transcript=transcript,
                segments=segments,
                has_speech=has_speech,
                speech_percentage=(
                    sum(s.end - s.start for s in segments) / 100.0  # Rough estimate
                ),
            )

            logger.info(
                f"Speech recognition complete",
                extra={"transcript_length": len(transcript), "segments": len(segments)}
            )

            return speech

        except Exception as e:
            logger.error(f"Speech recognition failed: {str(e)}")
            return Speech(
                transcript="",
                segments=[],
                has_speech=False,
                speech_percentage=0.0
            )
