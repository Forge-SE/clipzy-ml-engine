"""Compatibility wrapper for Stage 5 style transfer."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.pipelines.style_transfer import StyleTransferProcessor


class StyleApplier:
    """Backward-compatible wrapper around StyleTransferProcessor."""

    @staticmethod
    def apply(
        input_video_path: str,
        style: Any,
        output_path: str,
    ) -> dict[str, Any]:
        """Apply styling from a dict, Pydantic model, or style.json path."""
        style_source: str | Path | dict[str, Any]
        temp_path: Path | None = None

        if isinstance(style, (str, Path)):
            style_source = style
        elif hasattr(style, "model_dump"):
            style_source = style.model_dump()
        elif isinstance(style, dict):
            style_source = style
        else:
            style_source = json.loads(json.dumps(style))

        if isinstance(style_source, dict):
            with NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
                json.dump(style_source, handle, indent=2)
                temp_path = Path(handle.name)
            style_source = temp_path

        try:
            processor = StyleTransferProcessor(style_source)
            return processor.process(input_video_path=input_video_path, output_path=output_path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
