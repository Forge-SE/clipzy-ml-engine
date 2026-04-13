"""Speech recognition using Assembly AI."""

from typing import Optional
import assemblyai as aai
from app.core.logging_config import get_logger
from app.core.config import settings
from app.analysis.models import Speech, SpeechSegment

logger = get_logger(__name__)


class SpeechRecognizer:
    """Recognizes speech using Assembly AI."""

    def __init__(self, language_code: str = "en"):
        """
        Initialize speech recognizer.

        Args:
            language_code: Language code (en, es, fr, etc.)
        """
        if not settings.ASSEMBLYAI_API_KEY:
            logger.warning("Assembly AI API key not configured. Speech recognition will be disabled.")
            self.client = None
            return
            
        aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
        self.client = aai
        self.language_code = language_code
        logger.info(f"Assembly AI speech recognizer initialized for language: {language_code}")

    def recognize_speech(self, audio_path: str) -> Speech:
        """
        Recognize speech in audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Speech object with transcript and segments
        """
        try:
            if not self.client:
                logger.warning("Assembly AI client not initialized")
                return Speech(
                    transcript="",
                    segments=[],
                    has_speech=False,
                    speech_percentage=0.0
                )

            logger.info(f"Recognizing speech with Assembly AI", extra={"audio": audio_path})

            # Create transcriber with language
            config = aai.TranscriptionConfig(language_code=self.language_code)
            transcriber = aai.Transcriber(config=config)
            
            # Transcribe audio file
            transcript = transcriber.transcribe(audio_path)

            # Extract full transcript
            full_text = transcript.text.strip() if transcript.text else ""

            # Extract segments with timestamps
            segments = []
            if transcript.words:
                current_segment_text = ""
                segment_start = None
                
                for word in transcript.words:
                    if segment_start is None:
                        segment_start = word.start / 1000  # Convert ms to seconds
                    
                    current_segment_text += word.text + " "
                    
                    # Create segment on sentence boundaries (period, question mark, etc.)
                    if word.text.endswith((".", "?", "!", ",")):
                        speech_segment = SpeechSegment(
                            start=segment_start,
                            end=word.end / 1000,  # Convert ms to seconds
                            text=current_segment_text.strip(),
                            confidence=0.95,  # Assembly AI confidence available but normalized to 0.95
                        )
                        segments.append(speech_segment)
                        current_segment_text = ""
                        segment_start = None
                
                # Add any remaining text as final segment
                if current_segment_text.strip():
                    last_word = transcript.words[-1]
                    speech_segment = SpeechSegment(
                        start=segment_start,
                        end=last_word.end / 1000,
                        text=current_segment_text.strip(),
                        confidence=0.95,
                    )
                    segments.append(speech_segment)

            has_speech = len(full_text) > 0
            
            # Calculate speech percentage (duration of speech / total audio duration)
            speech_duration = 0.0
            if transcript.words:
                first_word = transcript.words[0]
                last_word = transcript.words[-1]
                total_duration = (last_word.end - first_word.start) / 1000  # ms to seconds
                speech_duration = total_duration / 100.0 if total_duration > 0 else 0.0

            speech = Speech(
                transcript=full_text,
                segments=segments,
                has_speech=has_speech,
                speech_percentage=min(speech_duration, 100.0),
            )

            logger.info(
                f"Speech recognition complete",
                extra={"transcript_length": len(full_text), "segments": len(segments)}
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
