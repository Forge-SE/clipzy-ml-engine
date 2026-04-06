#!/usr/bin/env python3
"""
Example script for running video analysis with the Video Analysis Engine.

Usage:
    python analyze_video.py path/to/video.mp4
    python analyze_video.py path/to/video.mp4 --device cuda --model large
"""

import json
import sys
from pathlib import Path
from typing import Optional

from app.analysis.pipeline import VideoAnalysisPipeline
from app.analysis.config import AnalysisConfig
from app.utils.progress_tracker import ProgressTracker


def analyze_video(
    video_path: str,
    output_path: Optional[str] = None,
    device: str = "cpu",
    whisper_model: str = "base",
    frame_sample_rate: int = 2,
) -> dict:
    """
    Analyze a video and save results to JSON.

    Args:
        video_path: Path to input video file
        output_path: Optional path to save JSON output
        device: Device to use (cpu or cuda)
        whisper_model: Whisper model size (tiny, small, base, medium, large)
        frame_sample_rate: Sample every Nth frame

    Returns:
        Analysis results dictionary
    """
    # Validate input
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if not video_file.is_file():
        raise ValueError(f"Not a file: {video_path}")

    # Create progress tracker
    progress = ProgressTracker(total_steps=8)
    progress.print_header("Video Analysis Engine")

    progress.print_detail("Input Video:", str(video_file))
    progress.print_detail("Device:", device)
    progress.print_detail("Model:", whisper_model)
    progress.print_detail("Frame Sampling:", f"Every {frame_sample_rate} frame(s)")
    progress.print_detail("Output:", output_path or f"{video_file.stem}_analysis.json")

    # Create configuration
    config = AnalysisConfig(
        device=device,
        whisper_model=whisper_model,
        frame_sample_rate=frame_sample_rate,
        whisper_fp16=(device == "cuda"),  # Use fp16 on GPU
    )

    # Initialize pipeline with progress tracker
    pipeline = VideoAnalysisPipeline(config=config, progress_tracker=progress)

    # Initialize progress steps
    for step_name in [
        "Video Ingestion",
        "Shot Detection",
        "Frame Extraction",
        "Motion Analysis",
        "Audio Extraction",
        "Audio Analysis & Speech Recognition",
        "Visual Embeddings & Color Analysis",
        "Results Aggregation"
    ]:
        progress.add_step(step_name)

    try:
        print("\n" + "="*70)
        print("Starting analysis...")
        print("="*70)

        style_dna = pipeline.analyze(str(video_file))

        # Print summary
        print(f"\n{'='*70}")
        print(f"Analysis Complete!")
        print(f"{'='*70}\n")

        print(f"Duration:           {style_dna.duration:.2f}s")
        print(f"Resolution:         {style_dna.resolution[0]}x{style_dna.resolution[1]}")
        print(f"FPS:                {style_dna.fps:.2f}\n")

        print(f"Shots detected:     {len(style_dna.cuts)}")
        if style_dna.pacing:
            print(f"Pacing type:        {style_dna.pacing.type}")
            print(f"Avg shot length:    {style_dna.pacing.avg_shot_duration:.2f}s\n")

        print(f"Motion timeline:    {len(style_dna.motion)} points")
        print(f"BPM:                {style_dna.audio.bpm:.1f}" if style_dna.audio and style_dna.audio.bpm else "BPM:                N/A")
        print(f"Beats detected:     {len(style_dna.audio.beats) if style_dna.audio else 0}")
        print(f"Speech segments:    {len(style_dna.speech.segments) if style_dna.speech else 0}")
        print(f"Visual embeddings:  {len(style_dna.visual.embedding_timestamps)}\n")

        if style_dna.color:
            print(f"Brightness:         {style_dna.color.brightness:.2f}")
            print(f"Saturation:         {style_dna.color.saturation:.2f}")
            print(f"Temperature:        {style_dna.color.color_temperature}\n")

        print(f"Jump cuts:          {style_dna.effects.has_jump_cuts}")
        print(f"Beat sync score:    {style_dna.effects.beat_sync_score:.2f}")
        print(f"Fast pacing:        {style_dna.effects.fast_pacing}\n")

        print(f"Confidence:         {style_dna.overall_confidence:.2%}")

        # Convert to dictionary
        results = style_dna.to_dict()

        # Save to JSON
        if output_path is None:
            output_path = video_file.stem + "_analysis.json"

        output_file = Path(output_path)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved:      {output_file}\n")

        return results

    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        raise

    finally:
        # Cleanup temp files
        print("Cleaning up temporary files...")
        pipeline.cleanup()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Video Analysis Engine - Extract style DNA from videos"
    )

    parser.add_argument(
        "video",
        help="Path to video file to analyze"
    )

    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSON file path (default: video_name_analysis.json)"
    )

    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Device to use for ML models (default: cpu)"
    )

    parser.add_argument(
        "--model",
        choices=["tiny", "small", "base", "medium", "large"],
        default="base",
        help="Whisper model size (default: base)"
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=2,
        help="Sample every Nth frame (default: 2)"
    )

    args = parser.parse_args()

    try:
        analyze_video(
            video_path=args.video,
            output_path=args.output,
            device=args.device,
            whisper_model=args.model,
            frame_sample_rate=args.sample_rate,
        )
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
