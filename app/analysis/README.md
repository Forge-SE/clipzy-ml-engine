# Video Analysis Engine Documentation

## Overview

The **Video Analysis Engine** is a production-ready Python module that extracts comprehensive style DNA from videos. It uses state-of-the-art computer vision, audio processing, and machine learning models to analyze videos across 8 independent dimensions.

## Architecture

### Core Components

The analysis engine is modularized into **8 independent analysis components**:

```
app/analysis/
├── config.py              # Configuration and constants
├── models.py              # Data structures for all analysis results
├── pipeline.py            # Main orchestration (8-step pipeline)
├── video_ingestion.py     # Video loading and audio extraction
├── shot_detection.py      # Shot boundaries via PySceneDetect
├── motion_analysis.py     # Optical flow via OpenCV
├── audio_analysis.py      # Tempo/beats via Librosa
├── speech_recognition.py  # Speech-to-text via Whisper
├── visual_embeddings.py   # Visual features via CLIP
├── color_analysis.py      # Color profiling (HSV analysis)
├── pacing_analyzer.py     # Shot pacing statistics
├── effect_heuristics.py   # Infer editing effects
└── style_aggregator.py    # Combine results into StyleDNA
```

### Technology Stack

| Layer | Library | Purpose |
|-------|---------|---------|
| **Video Processing** | OpenCV 4.8.1 | Frame extraction, optical flow, color analysis |
| **Shot Detection** | PySceneDetect 0.6.1 | Scene boundary detection |
| **Audio Analysis** | Librosa 0.10.0 | Tempo, beats, frequency analysis |
| **Speech Recognition** | OpenAI Whisper 20231213 | Speech-to-text with timestamps |
| **Visual Embeddings** | CLIP (Transformers 4.36.2) | Scene understanding & similarity |
| **Deep Learning** | PyTorch 2.1.1 | GPU support for Whisper & CLIP |
| **Image Processing** | Pillow 10.1.0 + scikit-image 0.22.0 | Color processing |
| **Audio I/O** | soundfile 0.12.1 | Audio file reading |

## Quick Start

### Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install analysis module specific packages
pip install opencv-python librosa scenedetect[opencv] openai-whisper transformers torch soundfile Pillow scikit-image
```

### Basic Usage

```python
from app.analysis.pipeline import VideoAnalysisPipeline
from app.analysis.config import AnalysisConfig

# Create pipeline with default config
pipeline = VideoAnalysisPipeline()

# Analyze video
style_dna = pipeline.analyze("path/to/video.mp4")

# Access results
print(f"Shots detected: {len(style_dna.cuts)}")
print(f"Tempo: {style_dna.audio.bpm} BPM")
print(f"Confidence: {style_dna.overall_confidence:.2%}")

# Get JSON output
style_dict = style_dna.to_dict()

# Cleanup temp files
pipeline.cleanup()
```

### Advanced Configuration

```python
from app.analysis.config import AnalysisConfig
from app.analysis.pipeline import VideoAnalysisPipeline

config = AnalysisConfig(
    # Frame sampling
    frame_sample_rate=2,  # Analyze every 2nd frame
    
    # Shot detection
    threshold=24.0,  # PySceneDetect sensitivity
    
    # Speech recognition
    whisper_model="base",  # Use smaller model
    device="cuda",  # Use GPU
    whisper_fp16=True,  # Half precision
    
    # Motion analysis
    motion_intensity_threshold=0.15,  # Sensitivity
)

pipeline = VideoAnalysisPipeline(config=config)
style_dna = pipeline.analyze("video.mp4")
```

## Analysis Components

### 1. Video Ingestion (`video_ingestion.py`)

Loads video and extracts frames efficiently.

```python
from app.analysis.video_ingestion import VideoIngestion

video = VideoIngestion("video.mp4")
print(video.duration)       # Total duration in seconds
print(video.fps)            # Frames per second
print(video.resolution)     # (width, height)

frames = video.extract_frames(sample_rate=2)  # Every 2nd frame
frame = video.get_frame_at_time(5.0)          # Frame at 5 seconds

audio_path = video.extract_audio("audio.wav")  # Extract with FFmpeg
```

### 2. Shot Detection (`shot_detection.py`)

Detects scene cuts and shot boundaries using PySceneDetect.

```python
from app.analysis.shot_detection import ShotDetector

detector = ShotDetector(threshold=24.0)
cuts = detector.detect_cuts("video.mp4")

for cut in cuts:
    print(f"Cut at {cut.timestamp:.2f}s (duration: {cut.shot_duration:.2f}s)")
```

**Output Structure:**
```python
Cut(
    timestamp: float,        # Where the cut happens
    confidence: float,       # 0-1 detection confidence
    shot_duration: float,    # Duration until next cut
)
```

### 3. Motion Analysis (`motion_analysis.py`)

Analyzes motion using OpenCV optical flow (Farneback algorithm).

```python
from app.analysis.motion_analysis import MotionAnalyzer

analyzer = MotionAnalyzer(sample_rate=4)
motion = analyzer.analyze_motion(frames, fps=30.0)

for m in motion:
    print(f"Motion at {m.timestamp:.2f}s: intensity {m.intensity:.2f}")
```

**Features:**
- Detects camera movement and object motion
- Generates motion intensity timeline
- Identifies motion spikes and static sections

### 4. Audio Analysis (`audio_analysis.py`)

Extracts tempo, beats, and audio characteristics using Librosa.

```python
from app.analysis.audio_analysis import AudioAnalyzer

analyzer = AudioAnalyzer(sample_rate=22050)
audio = analyzer.analyze_audio("audio.wav")

print(f"Tempo: {audio.bpm:.1f} BPM")
print(f"Beats detected: {len(audio.beats)}")
print(f"Dominant frequency: {audio.dominant_frequency:.1f} Hz")
```

**Features:**
- BPM detection using onset strength
- Beat frame detection
- Dominant frequency analysis
- Energy normalization

### 5. Speech Recognition (`speech_recognition.py`)

Speech-to-text using OpenAI Whisper with timestamp alignment.

```python
from app.analysis.speech_recognition import SpeechRecognizer

recognizer = SpeechRecognizer(
    model_name="base",
    device="cpu",
    fp16=False,
)

speech = recognizer.recognize_speech("audio.wav")

print(speech.transcript)
for segment in speech.segments:
    print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
```

**Model Sizes (CPU vs GPU):**
- `tiny` (39M) - 2s/min of audio on CPU
- `small` (141M) - 10s/min on CPU
- `base` (140M) - 15s/min on CPU (recommended)
- `medium` (769M) - Better accuracy, slower
- `large` (1550M) - Best accuracy, GPU recommended

### 6. Visual Embeddings (`visual_embeddings.py`)

Generates visual embeddings using CLIP for scene understanding.

```python
from app.analysis.visual_embeddings import VisualEmbedder

embedder = VisualEmbedder(
    model_name="openai/clip-vit-base-patch32",
    device="cuda"
)

embeddings, timestamps = embedder.embed_frames(frames, sample_rate=30)
similarities = embedder.compute_similarity_sequence(embeddings)

# High similarity = similar scenes
# Low similarity = scene change / jump cut
for ts, sim in zip(timestamps[:-1], similarities):
    if sim < 0.8:
        print(f"Potential jump cut at {ts:.2f}s (similarity: {sim:.2f})")
```

**Features:**
- Per-frame visual embeddings (512-dimensional)
- Scene similarity detection
- Jump cut identification
- GPU accelerated (batch processing)

### 7. Color Analysis (`color_analysis.py`)

Extracts color statistics from video frames.

```python
from app.analysis.color_analysis import ColorAnalyzer

analyzer = ColorAnalyzer()
color = analyzer.analyze_frames(frames, sample_rate=5)

print(f"Brightness: {color.brightness:.2f}")
print(f"Saturation: {color.saturation:.2f}")
print(f"Dominant colors: {color.dominant_color_names}")
print(f"Temperature: {color.color_temperature}")
```

**Metrics:**
- `brightness`: 0-1 (0=dark, 1=bright)
- `saturation`: 0-1 (0=grayscale, 1=vivid)
- `contrast`: 0-1 (std deviation of luminance)
- `dominant_colors`: RGB tuples + names
- `color_temperature`: warm/neutral/cool

### 8. Effect Heuristics (`effect_heuristics.py`)

Infers editing effects using heuristics from other analyses.

```python
from app.analysis.effect_heuristics import EffectHeuristics

detector = EffectHeuristics(
    motion_intensity_threshold=0.15,
    jump_cut_threshold=0.8,
)

effects = detector.detect_effects(
    cuts=cuts,
    motion=motion,
    beats=audio.beats,
    similarities=similarities,
    total_duration=duration,
    avg_shot_duration=pacing.avg_shot_duration,
)

print(f"Jump cuts: {effects.has_jump_cuts}")
print(f"Fast pacing: {effects.fast_pacing}")
print(f"Motion heavy: {effects.motion_heavy}")
print(f"Beat sync score: {effects.beat_sync_score:.2f}")
```

**Detected Effects:**
- **Jump cuts**: High similarity between consecutive shots
- **Fast pacing**: Average shot duration < 2 seconds
- **Motion heavy**: Average motion intensity > 0.3
- **Beat sync**: % of cuts aligned with audio beats
- **Zoom frequency**: Detected motion intensity spikes

## Output Data Structures

### StyleDNA (Top-level Result)

```python
@dataclass
class StyleDNA:
    # Metadata
    video_path: str
    duration: float              # Total duration in seconds
    fps: float
    resolution: tuple[int, int]  # (width, height)
    created_at: datetime
    
    # Analysis results
    cuts: list[Cut]
    pacing: Pacing
    motion: list[Motion]
    audio: Audio
    speech: Speech
    visual: Visual
    color: Color
    effects: Effects
    
    overall_confidence: float    # 0-1, weighted average
    
    # Export to JSON
    def to_dict(self) -> dict: ...
```

### Individual Components

**Cut:**
```python
Cut(
    timestamp: float,          # Seconds from start
    confidence: float,         # 0-1 detection confidence
    shot_duration: float,      # Duration until next cut
)
```

**Pacing:**
```python
Pacing(
    avg_shot_duration: float,  # Average seconds per shot
    variance: float,           # Variance of shot lengths
    type: str,                 # "fast"/"medium"/"slow"
    total_shots: int,
)
```

**Motion:**
```python
Motion(
    timestamp: float,          # Seconds from start
    intensity: float,          # 0-1, normalized motion magnitude
    direction: Optional[str],  # "horizontal"/"vertical"/etc
)
```

**Beat:**
```python
Beat(
    timestamp: float,          # Seconds from start
    confidence: float,         # 0-1
)
```

**SpeechSegment:**
```python
SpeechSegment(
    start: float,              # Seconds
    end: float,
    text: str,
    confidence: float = 0.95,  # Whisper confidence
)
```

**Color:**
```python
Color(
    brightness: float,         # 0-1
    contrast: float,           # 0-1
    saturation: float,         # 0-1
    dominant_colors: list[tuple[int, int, int]],  # RGB
    dominant_color_names: list[str],
    color_temperature: str,    # "warm"/"neutral"/"cool"
)
```

## Configuration

### AnalysisConfig Options

```python
@dataclass
class AnalysisConfig:
    # Video sampling
    frame_sample_rate: int = 2           # Sample every Nth frame
    max_frames_for_clip: int = 1000
    extract_every_n_frames: int = 30     # CLIP embedding frequency
    
    # Shot detection
    threshold: float = 24.0              # PySceneDetect threshold
    min_scene_length: float = 0.5        # Minimum shot duration
    
    # Motion analysis
    motion_sample_rate: int = 4
    
    # Audio
    sample_rate: int = 22050             # Librosa
    
    # Speech recognition
    whisper_model: str = "base"
    device: str = "cpu"                  # or "cuda"
    whisper_fp16: bool = False           # Enable for GPU
    
    # CLIP
    clip_model_name: str = "openai/clip-vit-base-patch32"
    clip_batch_size: int = 32
    
    # Color analysis
    color_sample_rate: int = 5
    
    # Heuristics
    motion_intensity_threshold: float = 0.15
    jump_cut_threshold: float = 0.8
    
    # Output
    temp_dir: Path = Path("./tmp_analysis")
```

## Performance Optimization

### For Faster Analysis (Low Quality)
```python
config = AnalysisConfig(
    frame_sample_rate=4,           # Skip more frames
    whisper_model="tiny",          # Smaller model
    extract_every_n_frames=60,     # Less frequent embeddings
)
```

### For Better Quality (Slower)
```python
config = AnalysisConfig(
    frame_sample_rate=1,           # Every frame
    whisper_model="large",         # Best quality
    device="cuda",                 # GPU acceleration
    whisper_fp16=True,
    extract_every_n_frames=10,     # More embeddings
)
```

### GPU Acceleration

To use GPU (recommended for Whisper and CLIP):

```python
config = AnalysisConfig(
    device="cuda",
    whisper_fp16=True,  # Half precision (faster)
)
pipeline = VideoAnalysisPipeline(config=config)
```

## Integration with FastAPI Pipeline

The analysis engine integrates seamlessly with the existing FastAPI backend:

```python
# In app/pipelines/video_analysis.py
from app.analysis.pipeline import VideoAnalysisPipeline

class VideoAnalyzer:
    @staticmethod
    def analyze(video_path: str) -> dict:
        pipeline = VideoAnalysisPipeline()
        style_dna = pipeline.analyze(video_path)
        return style_dna.to_dict()  # Returns full analysis
```

## Error Handling

```python
from app.analysis.pipeline import VideoAnalysisPipeline

try:
    pipeline = VideoAnalysisPipeline()
    style_dna = pipeline.analyze("video.mp4")
except FileNotFoundError as e:
    print(f"Video not found: {e}")
except RuntimeError as e:
    print(f"Analysis failed: {e}")
finally:
    pipeline.cleanup()  # Always cleanup temp files
```

## Example Output (JSON)

```json
{
  "metadata": {
    "video_path": "video.mp4",
    "duration": 60.0,
    "fps": 30.0,
    "resolution": [1920, 1080],
    "created_at": "2024-01-15T10:30:00.123456"
  },
  "cuts": [
    {
      "timestamp": 0.0,
      "confidence": 0.95,
      "shot_duration": 3.2
    },
    {
      "timestamp": 3.2,
      "confidence": 0.94,
      "shot_duration": 2.8
    }
  ],
  "pacing": {
    "avg_shot_duration": 3.0,
    "variance": 0.45,
    "type": "fast",
    "total_shots": 20
  },
  "motion": {
    "timeline": [
      { "timestamp": 0.0, "intensity": 0.2 },
      { "timestamp": 0.1, "intensity": 0.3 }
    ],
    "peaks": [...]
  },
  "audio": {
    "bpm": 120.0,
    "beats": [
      { "timestamp": 0.0, "confidence": 0.95 },
      { "timestamp": 0.5, "confidence": 0.92 }
    ],
    "dominant_frequency": 440.0,
    "energy": 0.65
  },
  "speech": {
    "transcript": "Hello everyone. Welcome to my channel.",
    "segments": [
      {
        "start": 0.1,
        "end": 1.5,
        "text": "Hello everyone.",
        "confidence": 0.95
      }
    ],
    "has_speech": true,
    "speech_percentage": 0.45
  },
  "visual": {
    "embedding_timestamps": [0.0, 1.0, 2.0],
    "avg_brightness": 0.65,
    "avg_contrast": 0.5,
    "scene_similarity_average": 0.85
  },
  "color": {
    "brightness": 0.65,
    "contrast": 0.5,
    "saturation": 0.7,
    "dominant_color_names": ["Blue", "White", "Gray"],
    "color_temperature": "neutral"
  },
  "effects": {
    "has_jump_cuts": false,
    "zoom_frequency": 0.15,
    "beat_sync_score": 0.8,
    "fast_pacing": true,
    "motion_heavy": false,
    "talking_head": false,
    "scene_cuts_count": 20
  },
  "overall_confidence": 0.92
}
```

## Limitations & Future Work

### Current Limitations
- Motion analysis assumes camera-dominant scenes
- Speech recognition limited to single language (English)
- Color analysis uses simple k-means clustering
- Effect heuristics are rule-based (not ML-based)

### Future Enhancements
- [ ] Multi-language speech recognition
- [ ] Deep learning based effect classification
- [ ] Object tracking for detailed motion analysis
- [ ] Face detection and expression analysis
- [ ] Scene classification (indoor, outdoor, etc.)
- [ ] Credit/title card detection
- [ ] Music genre classification

## Troubleshooting

### FFmpeg not found
```bash
# Windows
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

### GPU Memory Issues
```python
config = AnalysisConfig(
    device="cpu",  # Fallback to CPU
    whisper_model="small",  # Smaller model
    clip_batch_size=8,  # Smaller batches
)
```

### Out of Memory on Video
```python
config = AnalysisConfig(
    frame_sample_rate=4,  # Skip more frames
    extract_every_n_frames=60,  # Less frequent embeddings
)
```

## References

- **PySceneDetect**: https://www.scenedetect.com/
- **Librosa**: https://librosa.org/
- **OpenAI Whisper**: https://github.com/openai/whisper
- **CLIP**: https://github.com/openai/CLIP
- **OpenCV**: https://opencv.org/

## License

This video analysis engine is part of the Clipzy infra project.
