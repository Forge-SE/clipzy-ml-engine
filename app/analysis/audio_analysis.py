"""Audio analysis using Librosa."""

from typing import Optional

import librosa
import numpy as np
from app.core.logging_config import get_logger
from app.analysis.models import Audio, Beat

logger = get_logger(__name__)


class AudioAnalyzer:
    """Analyzes audio properties including tempo and beats."""

    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def analyze_audio(self, audio_path: str) -> Audio:
       
        try:
           
            y, sr = librosa.load(audio_path, sr=self.sample_rate)

            logger.info(
                f"Audio loaded",
                extra={"duration": len(y) / sr, "sample_rate": sr}
            )

            # Estimate tempo and beat frames
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)

            # Convert beat frames to seconds
            beat_times = librosa.frames_to_time(beats, sr=sr)
            beat_objects = [
                Beat(timestamp=float(t), confidence=0.9)
                for t in beat_times
            ]

            # Calculate energy
            energy = librosa.feature.melspectrogram(y=y, sr=sr)
            avg_energy = float(np.mean(energy))

            # Dominant frequency
            fft = np.fft.rfft(y)
            magnitude = np.abs(fft)
            freqs = np.fft.rfftfreq(len(y), d=1.0 / sr)
            dominant_freq = freqs[np.argmax(magnitude)]

            audio = Audio(
                bpm=float(tempo),
                beats=beat_objects,
                dominant_frequency=float(dominant_freq),
                energy=avg_energy,
            )

            logger.info(
                f"Audio analysis complete",
                extra={"bpm": tempo, "beats": len(beat_objects), "energy": avg_energy}
            )

            return audio

        except Exception as e:
            logger.error(f"Audio analysis failed: {str(e)}")
            return Audio()  
