"""Audio analysis pipeline."""

from typing import Any
from pathlib import Path

from app.core.logging_config import get_logger
from app.analysis.audio_analysis import AudioAnalyzer as LibrosaAnalyzer
from app.analysis.speech_recognition import SpeechRecognizer
from app.analysis.config import AnalysisConfig

logger = get_logger(__name__)


class AudioAnalyzer:
    """Analyzes audio: speech, music, beats, dynamics, etc."""

    @staticmethod
    def analyze(audio_path: str, config: AnalysisConfig = None) -> dict[str, Any]:
        """
        Analyze audio for speech, music, beats, and dynamics.

        Uses Librosa for tempo/beat detection and OpenAI Whisper for speech recognition.

        Args:
            audio_path: Path to audio file (or video file to extract audio from)
            config: Optional analysis configuration

        Returns:
            Dictionary with audio analysis results
        """
        logger.info(f"Starting audio analysis", extra={"audio_path": audio_path})

        config = config or AnalysisConfig()

        try:
            # Analyze audio with Librosa
            analyzer = LibrosaAnalyzer(sample_rate=config.sample_rate)
            audio_data = analyzer.analyze_audio(audio_path)

            # Recognize speech with Whisper
            speech_data = None
            try:
                recognizer = SpeechRecognizer(
                    model_name=config.whisper_model,
                    device=config.device,
                    fp16=config.whisper_fp16,
                )
                speech_data = recognizer.recognize_speech(audio_path)
            except Exception as e:
                logger.warning(f"Speech recognition failed: {str(e)}")

            # Build analysis dictionary
            analysis = {
                "has_speech": speech_data.has_speech if speech_data else False,
                "has_music": audio_data.bpm is not None,
                "speech_transcript": speech_data.transcript if speech_data else "",
                "speech_segments": [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "confidence": seg.confidence,
                    }
                    for seg in (speech_data.segments if speech_data else [])
                ],
                "tempo_bpm": audio_data.bpm,
                "beats": [
                    {
                        "timestamp": beat.timestamp,
                        "confidence": beat.confidence,
                    }
                    for beat in audio_data.beats
                ],
                "dominant_frequency": audio_data.dominant_frequency,
                "energy": audio_data.energy,
            }

            logger.info(
                f"Audio analysis complete",
                extra={
                    "audio_path": audio_path,
                    "bpm": audio_data.bpm,
                    "beats": len(audio_data.beats),
                }
            )

            return analysis

        except Exception as e:
            logger.error(
                f"Audio analysis failed: {str(e)}",
                extra={"audio_path": audio_path}
            )
            raise
