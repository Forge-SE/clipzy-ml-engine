"""Compatibility wrapper for Stage 6 rendering."""

from __future__ import annotations

from typing import Any

from app.pipelines.renderer import Renderer


class VideoRenderer:
    """Backward-compatible wrapper around Renderer."""

    @staticmethod
    def render(
        video_path: str,
        output_path: str,
        quality: str = "high",
        source_video_path: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Render the final output, defaulting audio source to the input video."""
        renderer = Renderer()
        render_config = dict(config or {})
        render_config.setdefault("quality", quality)
        return renderer.render(
            styled_video_path=video_path,
            source_video_path=source_video_path or video_path,
            output_path=output_path,
            config=render_config,
        )
