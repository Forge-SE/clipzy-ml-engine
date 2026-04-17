"""Stage 5 style transfer processor."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from app.core.logging_config import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int], None]


@dataclass(slots=True)
class ResolvedStyle:
    """Normalized style parameters ready for frame processing."""

    brightness_offset: float = 0.0
    contrast_factor: float = 1.0
    saturation_factor: float = 1.0
    red_factor: float = 1.0
    green_factor: float = 1.0
    blue_factor: float = 1.0
    grain_intensity: float = 0.0
    vignette_intensity: float = 0.0
    sharpen_amount: float = 0.0
    sharpen_radius: float = 1.0
    letterbox_ratio: float | None = None
    lut_path: Path | None = None


class CubeLUT:
    """Simple 3D LUT reader for .cube files."""

    def __init__(
        self,
        table: np.ndarray,
        domain_min: np.ndarray | None = None,
        domain_max: np.ndarray | None = None,
    ) -> None:
        self.table = table.astype(np.float32)
        self.size = table.shape[0]
        self.domain_min = (
            domain_min.astype(np.float32)
            if domain_min is not None
            else np.array([0.0, 0.0, 0.0], dtype=np.float32)
        )
        self.domain_max = (
            domain_max.astype(np.float32)
            if domain_max is not None
            else np.array([1.0, 1.0, 1.0], dtype=np.float32)
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "CubeLUT":
        """Load a .cube LUT from disk."""
        file_path = Path(path)
        size: int | None = None
        domain_min = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        domain_max = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        entries: list[list[float]] = []

        for raw_line in file_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("TITLE"):
                continue
            if line.startswith("DOMAIN_MIN"):
                domain_min = np.array(
                    [float(value) for value in line.split()[1:4]],
                    dtype=np.float32,
                )
                continue
            if line.startswith("DOMAIN_MAX"):
                domain_max = np.array(
                    [float(value) for value in line.split()[1:4]],
                    dtype=np.float32,
                )
                continue
            if line.startswith("LUT_3D_SIZE"):
                size = int(line.split()[-1])
                continue

            parts = line.split()
            if len(parts) == 3:
                entries.append([float(value) for value in parts])

        if size is None:
            raise ValueError(f"Missing LUT_3D_SIZE in {file_path}")

        expected_entries = size ** 3
        if len(entries) != expected_entries:
            raise ValueError(
                f"Expected {expected_entries} LUT entries in {file_path}, found {len(entries)}"
            )

        table = np.array(entries, dtype=np.float32).reshape((size, size, size, 3))
        return cls(table=table, domain_min=domain_min, domain_max=domain_max)

    def apply(self, rgb_frame: np.ndarray) -> np.ndarray:
        """Apply trilinear LUT sampling to an RGB float frame."""
        clipped = np.clip(rgb_frame, 0.0, 1.0)
        normalized = (clipped - self.domain_min) / np.maximum(
            self.domain_max - self.domain_min,
            1e-6,
        )
        normalized = np.clip(normalized, 0.0, 1.0)

        coords = normalized * (self.size - 1)
        lower = np.floor(coords).astype(np.int32)
        upper = np.clip(lower + 1, 0, self.size - 1)
        frac = coords - lower

        r0, g0, b0 = lower[..., 0], lower[..., 1], lower[..., 2]
        r1, g1, b1 = upper[..., 0], upper[..., 1], upper[..., 2]

        c000 = self.table[r0, g0, b0]
        c001 = self.table[r0, g0, b1]
        c010 = self.table[r0, g1, b0]
        c011 = self.table[r0, g1, b1]
        c100 = self.table[r1, g0, b0]
        c101 = self.table[r1, g0, b1]
        c110 = self.table[r1, g1, b0]
        c111 = self.table[r1, g1, b1]

        fx = frac[..., 0][..., None]
        fy = frac[..., 1][..., None]
        fz = frac[..., 2][..., None]

        c00 = c000 * (1.0 - fz) + c001 * fz
        c01 = c010 * (1.0 - fz) + c011 * fz
        c10 = c100 * (1.0 - fz) + c101 * fz
        c11 = c110 * (1.0 - fz) + c111 * fz
        c0 = c00 * (1.0 - fy) + c01 * fy
        c1 = c10 * (1.0 - fy) + c11 * fy

        return np.clip(c0 * (1.0 - fx) + c1 * fx, 0.0, 1.0)


class StyleTransferProcessor:
    """Apply style JSON instructions frame by frame."""

    def __init__(self, style_source: str | Path | dict[str, Any]) -> None:
        self.style_source = style_source
        self.style_json_path: Path | None = (
            Path(style_source)
            if isinstance(style_source, (str, Path))
            else None
        )
        self.style_data = self._load_style(style_source)
        self.resolved_style = self._resolve_style(self.style_data)
        self._lut = self._load_lut(self.resolved_style.lut_path)
        self._vignette_mask_cache: dict[tuple[int, int], np.ndarray] = {}
        self._rng = np.random.default_rng(42)

    def process(
        self,
        input_video_path: str | Path,
        output_path: str | Path,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Process an input video and write the styled output."""
        source_path = Path(input_video_path)
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(source_path))
        if not cap.isOpened():
            raise ValueError(f"Could not open input video: {source_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if width <= 0 or height <= 0:
            cap.release()
            raise ValueError(f"Could not determine video dimensions for {source_path}")

        writer = cv2.VideoWriter(
            str(destination),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            cap.release()
            raise ValueError(f"Could not open output video for writing: {destination}")

        active_effects = self._active_effects(width, height)
        started_at = time.perf_counter()
        processed_frames = 0

        logger.info(
            "Starting style transfer",
            extra={
                "input": str(source_path),
                "output": str(destination),
                "effects": active_effects,
            },
        )

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                styled_frame = self._apply_frame_effects(frame, processed_frames)
                writer.write(styled_frame)
                processed_frames += 1

                if progress_callback and frame_count > 0:
                    if processed_frames % 12 == 0 or processed_frames == frame_count:
                        progress_callback(processed_frames, frame_count)
        finally:
            cap.release()
            writer.release()

        elapsed = time.perf_counter() - started_at

        result = {
            "output_video_path": str(destination),
            "style_json_path": str(self.style_json_path) if self.style_json_path else None,
            "processing_time_seconds": round(elapsed, 3),
            "frame_count": processed_frames,
            "fps": round(float(fps), 3),
            "resolution": f"{width}x{height}",
            "active_effects": active_effects,
            "status": "success",
        }

        logger.info(
            "Style transfer complete",
            extra={
                "output": str(destination),
                "frames": processed_frames,
                "processing_time_seconds": result["processing_time_seconds"],
            },
        )
        return result

    def _load_style(self, style_source: str | Path | dict[str, Any]) -> dict[str, Any]:
        if isinstance(style_source, dict):
            return style_source
        style_path = Path(style_source)
        return json.loads(style_path.read_text(encoding="utf-8"))

    def _resolve_style(self, style_data: dict[str, Any]) -> ResolvedStyle:
        brightness_delta = self._get_percent(
            style_data,
            ("brightness",),
            ("adjustments", "brightness"),
            ("color_grade", "brightness"),
        )
        contrast_factor = self._get_factor(
            style_data,
            factor_paths=[("contrast_factor",), ("adjustments", "contrast_factor")],
            percent_paths=[("contrast",), ("adjustments", "contrast"), ("color_grade", "contrast")],
        )
        saturation_factor = self._get_factor(
            style_data,
            factor_paths=[("saturation_factor",), ("adjustments", "saturation_factor")],
            percent_paths=[("saturation",), ("adjustments", "saturation"), ("color_grade", "saturation")],
        )

        channels = self._lookup(style_data, ("channels",)) or {}
        channel_grade = self._lookup(style_data, ("channel_grade",)) or {}
        rgb_grade = self._lookup(style_data, ("rgb",)) or {}

        lut_value = self._lookup(
            style_data,
            ("lut_path",),
            ("lut",),
            ("lut", "path"),
            ("cube_lut",),
            ("cube_lut", "path"),
        )
        lut_path = self._resolve_optional_path(lut_value)

        sharpen_amount = self._get_unit_value(
            style_data,
            ("sharpen",),
            ("sharpening",),
            ("unsharp_mask", "amount"),
        )
        sharpen_radius = self._get_float(
            style_data,
            ("unsharp_mask", "radius"),
            default=1.0,
        )

        return ResolvedStyle(
            brightness_offset=brightness_delta / 100.0,
            contrast_factor=contrast_factor,
            saturation_factor=saturation_factor,
            red_factor=self._get_channel_factor("red", channels, channel_grade, rgb_grade, style_data),
            green_factor=self._get_channel_factor("green", channels, channel_grade, rgb_grade, style_data),
            blue_factor=self._get_channel_factor("blue", channels, channel_grade, rgb_grade, style_data),
            grain_intensity=self._get_unit_value(
                style_data,
                ("film_grain",),
                ("grain",),
                ("effects", "grain"),
            ),
            vignette_intensity=self._get_unit_value(
                style_data,
                ("vignette",),
                ("effects", "vignette"),
            ),
            sharpen_amount=sharpen_amount,
            sharpen_radius=max(sharpen_radius, 0.1),
            letterbox_ratio=self._parse_ratio(
                self._lookup(
                    style_data,
                    ("letterbox",),
                    ("letterbox", "aspect_ratio"),
                    ("cinematic_ratio",),
                    ("aspect_ratio",),
                )
            ),
            lut_path=lut_path,
        )

    def _apply_frame_effects(self, frame: np.ndarray, frame_index: int) -> np.ndarray:
        working = frame.astype(np.float32) / 255.0

        if self.resolved_style.contrast_factor != 1.0 or self.resolved_style.brightness_offset != 0.0:
            working = np.clip(
                ((working - 0.5) * self.resolved_style.contrast_factor) + 0.5 + self.resolved_style.brightness_offset,
                0.0,
                1.0,
            )

        if self.resolved_style.saturation_factor != 1.0:
            hsv = cv2.cvtColor(working, cv2.COLOR_BGR2HSV)
            hsv[..., 1] = np.clip(hsv[..., 1] * self.resolved_style.saturation_factor, 0.0, 1.0)
            working = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        if (
            self.resolved_style.red_factor != 1.0
            or self.resolved_style.green_factor != 1.0
            or self.resolved_style.blue_factor != 1.0
        ):
            working[..., 2] *= self.resolved_style.red_factor
            working[..., 1] *= self.resolved_style.green_factor
            working[..., 0] *= self.resolved_style.blue_factor
            working = np.clip(working, 0.0, 1.0)

        if self._lut is not None:
            rgb = cv2.cvtColor(working, cv2.COLOR_BGR2RGB)
            rgb = self._lut.apply(rgb)
            working = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if self.resolved_style.grain_intensity > 0.0:
            grain_stddev = 0.12 * self.resolved_style.grain_intensity
            noise = self._rng.normal(0.0, grain_stddev, working.shape).astype(np.float32)
            working = np.clip(working + noise, 0.0, 1.0)

        if self.resolved_style.vignette_intensity > 0.0:
            mask = self._get_vignette_mask(frame.shape[0], frame.shape[1])
            working = np.clip(working * mask[..., None], 0.0, 1.0)

        if self.resolved_style.sharpen_amount > 0.0:
            blurred = cv2.GaussianBlur(working, (0, 0), self.resolved_style.sharpen_radius)
            working = np.clip(
                working * (1.0 + self.resolved_style.sharpen_amount)
                - blurred * self.resolved_style.sharpen_amount,
                0.0,
                1.0,
            )

        output = np.clip(working * 255.0, 0.0, 255.0).astype(np.uint8)

        if self._should_letterbox(frame.shape[1], frame.shape[0]):
            output = self._apply_letterbox(output)

        return output

    def _active_effects(self, width: int, height: int) -> list[str]:
        effects: list[str] = []
        if self.resolved_style.contrast_factor != 1.0:
            effects.append("contrast")
        if self.resolved_style.brightness_offset != 0.0:
            effects.append("brightness")
        if self.resolved_style.saturation_factor != 1.0:
            effects.append("saturation")
        if (
            self.resolved_style.red_factor != 1.0
            or self.resolved_style.green_factor != 1.0
            or self.resolved_style.blue_factor != 1.0
        ):
            effects.append("channel_grade")
        if self._lut is not None:
            effects.append("lut")
        if self.resolved_style.grain_intensity > 0.0:
            effects.append("film_grain")
        if self.resolved_style.vignette_intensity > 0.0:
            effects.append("vignette")
        if self.resolved_style.sharpen_amount > 0.0:
            effects.append("unsharp_mask")
        if self._should_letterbox(width, height):
            effects.append("letterbox")
        return effects

    def _should_letterbox(self, width: int, height: int) -> bool:
        if self.resolved_style.letterbox_ratio is None:
            return False
        source_ratio = width / max(height, 1)
        return abs(source_ratio - self.resolved_style.letterbox_ratio) > 0.02

    def _apply_letterbox(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        target_ratio = self.resolved_style.letterbox_ratio
        if target_ratio is None:
            return frame

        current_ratio = width / max(height, 1)
        output = frame.copy()

        if target_ratio > current_ratio:
            visible_height = int(round(width / target_ratio))
            visible_height = max(min(visible_height, height), 0)
            pad = max((height - visible_height) // 2, 0)
            output[:pad, :] = 0
            output[height - pad :, :] = 0
        else:
            visible_width = int(round(height * target_ratio))
            visible_width = max(min(visible_width, width), 0)
            pad = max((width - visible_width) // 2, 0)
            output[:, :pad] = 0
            output[:, width - pad :] = 0

        return output

    def _get_vignette_mask(self, height: int, width: int) -> np.ndarray:
        cache_key = (height, width)
        if cache_key in self._vignette_mask_cache:
            return self._vignette_mask_cache[cache_key]

        x = np.linspace(-1.0, 1.0, width, dtype=np.float32)
        y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        radius = np.sqrt(xx ** 2 + yy ** 2)
        mask = 1.0 - np.clip(radius, 0.0, 1.0) * (0.85 * self.resolved_style.vignette_intensity)
        mask = np.clip(mask, 0.0, 1.0)
        self._vignette_mask_cache[cache_key] = mask
        return mask

    def _load_lut(self, lut_path: Path | None) -> CubeLUT | None:
        if lut_path is None:
            return None
        if not lut_path.exists():
            logger.warning(f"LUT file not found, skipping: {lut_path}")
            return None
        if lut_path.suffix.lower() != ".cube":
            logger.warning(f"Unsupported LUT format, expected .cube: {lut_path}")
            return None
        return CubeLUT.from_file(lut_path)

    def _resolve_optional_path(self, value: Any) -> Path | None:
        if value in (None, "", {}):
            return None
        path = Path(str(value))
        if path.is_absolute():
            return path
        if self.style_json_path is not None:
            return (self.style_json_path.parent / path).resolve()
        return path.resolve()

    def _parse_ratio(self, value: Any) -> float | None:
        if value in (None, "", {}):
            return None
        if isinstance(value, dict):
            return self._parse_ratio(value.get("aspect_ratio"))
        if isinstance(value, (int, float)):
            ratio = float(value)
            return ratio if ratio > 0.0 else None

        ratio_text = str(value).strip().lower()
        if not ratio_text:
            return None
        if ":" in ratio_text:
            left, right = ratio_text.split(":", 1)
            try:
                left_value = float(left)
                right_value = float(right)
                return left_value / right_value if right_value else None
            except ValueError:
                return None
        try:
            parsed = float(ratio_text)
            return parsed if parsed > 0.0 else None
        except ValueError:
            return None

    def _get_channel_factor(
        self,
        channel_name: str,
        channels: dict[str, Any],
        channel_grade: dict[str, Any],
        rgb_grade: dict[str, Any],
        style_data: dict[str, Any],
    ) -> float:
        short_name = channel_name[0]
        direct_factor = self._first_number(
            channels.get(f"{channel_name}_factor"),
            channels.get(f"{short_name}_factor"),
            channel_grade.get(f"{channel_name}_factor"),
            channel_grade.get(f"{short_name}_factor"),
            rgb_grade.get(f"{channel_name}_factor"),
            rgb_grade.get(f"{short_name}_factor"),
            self._lookup(style_data, (f"{channel_name}_factor",)),
            self._lookup(style_data, (f"{short_name}_factor",)),
        )
        if direct_factor is not None:
            return max(direct_factor, 0.0)

        delta = self._first_number(
            channels.get(channel_name),
            channels.get(short_name),
            channel_grade.get(channel_name),
            channel_grade.get(short_name),
            rgb_grade.get(channel_name),
            rgb_grade.get(short_name),
            self._lookup(style_data, (channel_name,)),
            self._lookup(style_data, (short_name,)),
        )
        return 1.0 + (delta or 0.0) / 100.0

    def _get_factor(
        self,
        style_data: dict[str, Any],
        *,
        factor_paths: list[tuple[str, ...]],
        percent_paths: list[tuple[str, ...]],
    ) -> float:
        direct_factor = self._get_float(style_data, *factor_paths, default=None)
        if direct_factor is not None:
            return max(float(direct_factor), 0.0)
        return 1.0 + self._get_percent(style_data, *percent_paths) / 100.0

    def _get_unit_value(self, style_data: dict[str, Any], *paths: tuple[str, ...]) -> float:
        raw = self._get_float(style_data, *paths, default=0.0)
        if raw <= 0.0:
            return 0.0
        if raw <= 1.0:
            return raw
        return min(raw / 100.0, 1.0)

    def _get_percent(self, style_data: dict[str, Any], *paths: tuple[str, ...]) -> float:
        return self._get_float(style_data, *paths, default=0.0)

    def _get_float(
        self,
        style_data: dict[str, Any],
        *paths: tuple[str, ...],
        default: float | None = 0.0,
    ) -> float | None:
        value = self._lookup(style_data, *paths)
        parsed = self._first_number(value)
        if parsed is None:
            return default
        return parsed

    def _lookup(self, style_data: dict[str, Any], *paths: tuple[str, ...]) -> Any:
        for path in paths:
            current: Any = style_data
            found = True
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    found = False
                    break
                current = current[key]
            if found:
                return current
        return None

    def _first_number(self, *values: Any) -> float | None:
        for value in values:
            if isinstance(value, dict):
                value = value.get("amount")
            if value in (None, "", {}):
                continue
            if isinstance(value, (int, float)):
                return float(value)
            try:
                return float(str(value).replace("%", "").strip())
            except ValueError:
                continue
        return None
