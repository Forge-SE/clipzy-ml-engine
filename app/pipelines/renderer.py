"""Stage 6 final renderer."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import cv2

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class Renderer:
    """Mux styled video with source audio and write the final MP4."""

    QUALITY_PRESETS = {
        "low": {"crf": 28, "preset": "veryfast"},
        "medium": {"crf": 23, "preset": "medium"},
        "high": {"crf": 18, "preset": "slow"},
    }

    def __init__(self, ffmpeg_binary: str | None = None) -> None:
        self.ffmpeg_binary = ffmpeg_binary or shutil.which("ffmpeg")

    def render(
        self,
        styled_video_path: str | Path,
        source_video_path: str | Path,
        output_path: str | Path,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Render the final deliverable."""
        config = self._merge_config(config or {})
        styled_path = Path(styled_video_path)
        source_path = Path(source_video_path)
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        started_at = time.perf_counter()
        warning: str | None = None
        ffmpeg_used = False
        audio_included = False

        if self.ffmpeg_binary:
            try:
                self._render_with_ffmpeg(
                    styled_path=styled_path,
                    source_path=source_path,
                    destination=destination,
                    config=config,
                )
                ffmpeg_used = True
                audio_included = True
            except subprocess.CalledProcessError as exc:
                warning = (
                    "FFmpeg render failed; falling back to OpenCV copy without audio."
                )
                logger.warning(
                    warning,
                    extra={"stderr": exc.stderr[-1000:] if exc.stderr else ""},
                )
                self._render_with_opencv_copy(
                    styled_path=styled_path,
                    destination=destination,
                    config=config,
                )
                audio_included = False
        else:
            warning = (
                "FFmpeg is not installed. Falling back to an OpenCV render copy without audio."
            )
            logger.warning(warning)
            self._render_with_opencv_copy(
                styled_path=styled_path,
                destination=destination,
                config=config,
            )

        metadata = self._probe_video(destination)
        elapsed = time.perf_counter() - started_at

        result = {
            "output_video_path": str(destination),
            "file_size_bytes": destination.stat().st_size if destination.exists() else 0,
            "duration_seconds": metadata["duration_seconds"],
            "codec": "h264" if ffmpeg_used else "mp4v",
            "bitrate": config.get("bitrate"),
            "frame_rate": metadata["frame_rate"],
            "resolution": metadata["resolution"],
            "rendering_time_seconds": round(elapsed, 3),
            "quality_level": config["quality"],
            "crf": config["crf"],
            "preset": config["preset"],
            "ffmpeg_used": ffmpeg_used,
            "audio_included": audio_included,
            "warning": warning,
            "status": "success",
        }

        logger.info(
            "Rendering complete",
            extra={
                "output": str(destination),
                "ffmpeg_used": ffmpeg_used,
                "audio_included": audio_included,
                "rendering_time_seconds": result["rendering_time_seconds"],
            },
        )
        return result

    def _render_with_ffmpeg(
        self,
        *,
        styled_path: Path,
        source_path: Path,
        destination: Path,
        config: dict[str, Any],
    ) -> None:
        vf_parts: list[str] = []
        scale_filter = self._build_ffmpeg_scale_filter(config)
        if scale_filter:
            vf_parts.append(scale_filter)

        command = [
            self.ffmpeg_binary or "ffmpeg",
            "-y",
            "-i",
            str(styled_path),
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0?",
        ]

        if vf_parts:
            command.extend(["-vf", ",".join(vf_parts)])

        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                str(config["preset"]),
                "-crf",
                str(config["crf"]),
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                str(config["audio_bitrate"]),
            ]
        )

        if config.get("bitrate"):
            command.extend(["-b:v", str(config["bitrate"])])

        command.extend(["-shortest", str(destination)])

        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )

        if completed.stderr:
            logger.info("FFmpeg render output", extra={"details": completed.stderr[-500:]})

    def _render_with_opencv_copy(
        self,
        *,
        styled_path: Path,
        destination: Path,
        config: dict[str, Any],
    ) -> None:
        cap = cv2.VideoCapture(str(styled_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open styled video: {styled_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        target_width, target_height = self._resolve_dimensions(
            source_width,
            source_height,
            config,
        )

        writer = cv2.VideoWriter(
            str(destination),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (target_width, target_height),
        )
        if not writer.isOpened():
            cap.release()
            raise ValueError(f"Could not write render output: {destination}")

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if (frame.shape[1], frame.shape[0]) != (target_width, target_height):
                    frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
                writer.write(frame)
        finally:
            cap.release()
            writer.release()

    def _merge_config(self, config: dict[str, Any]) -> dict[str, Any]:
        quality = str(config.get("quality", "high")).lower()
        merged = dict(self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["high"]))
        merged.update(config)
        merged["quality"] = quality
        merged.setdefault("audio_bitrate", "192k")
        merged.setdefault("resolution_scale", 1.0)
        return merged

    def _build_ffmpeg_scale_filter(self, config: dict[str, Any]) -> str | None:
        scale_width = config.get("scale_width")
        scale_height = config.get("scale_height")
        resolution_scale = float(config.get("resolution_scale", 1.0) or 1.0)

        if scale_width and scale_height:
            return f"scale={self._ensure_even(int(scale_width))}:{self._ensure_even(int(scale_height))}"

        if resolution_scale != 1.0:
            return (
                "scale="
                f"trunc(iw*{resolution_scale}/2)*2:"
                f"trunc(ih*{resolution_scale}/2)*2"
            )

        return None

    def _resolve_dimensions(
        self,
        width: int,
        height: int,
        config: dict[str, Any],
    ) -> tuple[int, int]:
        scale_width = config.get("scale_width")
        scale_height = config.get("scale_height")
        resolution_scale = float(config.get("resolution_scale", 1.0) or 1.0)

        if scale_width and scale_height:
            return self._ensure_even(int(scale_width)), self._ensure_even(int(scale_height))

        if resolution_scale != 1.0:
            return (
                self._ensure_even(max(int(width * resolution_scale), 2)),
                self._ensure_even(max(int(height * resolution_scale), 2)),
            )

        return self._ensure_even(width), self._ensure_even(height)

    def _probe_video(self, path: Path) -> dict[str, Any]:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise ValueError(f"Could not inspect rendered video: {path}")

        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            frame_rate = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        finally:
            cap.release()

        duration = (frame_count / frame_rate) if frame_rate > 0 else 0.0
        return {
            "duration_seconds": round(duration, 3),
            "frame_rate": round(frame_rate, 3),
            "resolution": f"{width}x{height}",
        }

    def _ensure_even(self, value: int) -> int:
        if value <= 2:
            return 2
        return value if value % 2 == 0 else value - 1
