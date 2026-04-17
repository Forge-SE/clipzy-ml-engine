"""Configuration for video analysis engine."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AnalysisConfig:
    """Configuration for video analysis."""

    # Video sampling
    frame_sample_rate: int = 2  # Sample every Nth frame
    max_frames_for_clip: int = 300  # Max frames for CLIP embeddings (reduced for faster processing)
    extract_every_n_frames: int = 100  # Extract embeddings every N frames (reduced frequency for speed)

    # Shot detection
    threshold: float = 24.0  # PySceneDetect threshold (default)
    min_scene_length: float = 0.5  # Minimum scene length in seconds

    # Motion analysis
    motion_sample_rate: int = 8  # Analyze every Nth frame for motion (increased for faster processing)

    # Audio
    sample_rate: int = 22050  # Librosa default

    # Speech recognition
    whisper_model: str = "tiny"  # tiny, small, base, medium, large (tiny for speed on CPU)
    device: str = "cpu"  # cpu or cuda
    whisper_fp16: bool = False

    # CLIP
    clip_model_name: str = "openai/clip-vit-base-patch32"
    clip_batch_size: int = 32

    # Color analysis
    color_sample_rate: int = 20  # Sample every Nth frame (increased for faster processing)

    # Heuristics
    motion_intensity_threshold: float = 0.15
    jump_cut_threshold: float = 0.8  # Cosine similarity for jump cuts

    # Output
    temp_dir: Path = Path("./tmp_analysis")

    def ensure_temp_dir(self) -> None:
        """Create temp directory if needed."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def cleanup_temp(self) -> None:
        """Clean up temporary files."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
