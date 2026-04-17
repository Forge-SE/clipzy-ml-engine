"""Integration glue for Stage 5 and Stage 6."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.constants import JobStatus, ProcessingStage
from app.core.logging_config import get_logger
from app.models import Job
from app.pipelines.renderer import Renderer
from app.pipelines.style_transfer import StyleTransferProcessor
from app.services import get_job_service, get_storage_service

logger = get_logger(__name__)

RENDER_CONFIG_KEYS = {
    "quality",
    "crf",
    "preset",
    "bitrate",
    "resolution_scale",
    "scale_width",
    "scale_height",
    "audio_bitrate",
}


def run_style_and_render(
    job: Job | dict[str, Any],
    style_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run Stage 5 and Stage 6 using the current job state.

    This accepts either the in-memory Job model or a plain job dictionary and
    writes the resulting artifact paths back into whichever object it received.
    """

    job_service = get_job_service()
    storage_service = get_storage_service()
    job_model = _coerce_job(job, job_service)
    job_id = job_model.job_id

    work_dir = settings.storage_path / "_work" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    source_video = job_service.get_video(job_model.video_id)
    if not source_video:
        raise ValueError(f"Video not found: {job_model.video_id}")

    source_video_path = _materialize_storage_asset(
        storage_path=source_video.storage_path,
        fallback_name=source_video.filename,
        destination_dir=work_dir,
    )

    style_data = _resolve_style_json(job_model, style_json)
    style_json_path = _ensure_style_json(
        style_data=style_data,
        work_dir=work_dir,
        existing_path=job_model.processing_config.get("style_json_path"),
    )

    job_service.append_job_log(
        job_id,
        message="Stage 5 started: style transfer",
        stage=ProcessingStage.STYLE_TRANSFER,
    )
    job_service.update_job_progress(
        job_id,
        JobStatus.PROCESSING,
        progress_percent=70,
        stage=ProcessingStage.STYLE_TRANSFER,
    )

    styled_video_path = work_dir / "styled_video.mp4"
    transfer_progress = {"last_percent": 70}

    def on_style_progress(done: int, total: int) -> None:
        if total <= 0:
            return
        percent = 70 + int((done / total) * 15)
        if percent > transfer_progress["last_percent"]:
            transfer_progress["last_percent"] = percent
            job_service.update_job_progress(
                job_id,
                JobStatus.PROCESSING,
                progress_percent=min(percent, 85),
                stage=ProcessingStage.STYLE_TRANSFER,
            )

    style_processor = StyleTransferProcessor(style_json_path)
    style_result = style_processor.process(
        input_video_path=source_video_path,
        output_path=styled_video_path,
        progress_callback=on_style_progress,
    )

    applied_effects = style_result.get("active_effects") or ["none"]
    job_service.append_job_log(
        job_id,
        message=f"Stage 5 complete: {', '.join(applied_effects)}",
        stage=ProcessingStage.STYLE_TRANSFER,
    )
    job_service.update_job_progress(
        job_id,
        JobStatus.PROCESSING,
        progress_percent=85,
        stage=ProcessingStage.STYLE_TRANSFER,
    )

    render_config = _resolve_render_config(job_model.processing_config)
    rendered_output_path = work_dir / "final_output.mp4"

    job_service.append_job_log(
        job_id,
        message="Stage 6 started: rendering",
        stage=ProcessingStage.RENDERING,
    )
    job_service.update_job_progress(
        job_id,
        JobStatus.PROCESSING,
        progress_percent=90,
        stage=ProcessingStage.RENDERING,
    )

    renderer = Renderer()
    render_result = renderer.render(
        styled_video_path=styled_video_path,
        source_video_path=source_video_path,
        output_path=rendered_output_path,
        config=render_config,
    )

    if render_result.get("warning"):
        job_service.append_job_log(
            job_id,
            message=render_result["warning"],
            stage=ProcessingStage.RENDERING,
            level="warning",
        )

    output_video_url = storage_service.save_file(
        Path(render_result["output_video_path"]),
        f"job_{job_id}",
    )

    result_paths = {
        "source_video_path": str(source_video_path),
        "style_json_path": str(style_json_path),
        "styled_video_path": str(styled_video_path),
        "rendered_video_path": str(rendered_output_path),
        "output_video_url": output_video_url,
    }

    job_service.set_job_result(
        job_id,
        style_json=style_data,
        output_video_url=output_video_url,
        result_paths=result_paths,
        render_metadata=render_result,
    )
    job_service.append_job_log(
        job_id,
        message="Stage 6 complete: final MP4 ready",
        stage=ProcessingStage.RENDERING,
    )
    job_service.update_job_progress(
        job_id,
        JobStatus.COMPLETED,
        progress_percent=100,
        stage=ProcessingStage.RENDERING,
    )

    latest_job = job_service.get_job(job_id)
    latest_job_dict = latest_job.to_dict()
    if isinstance(job, dict):
        job.clear()
        job.update(latest_job_dict)

    logger.info("Stage 5/6 pipeline complete", extra={"job_id": job_id})
    return latest_job_dict


def _coerce_job(job: Job | dict[str, Any], job_service) -> Job:
    if isinstance(job, Job):
        return job
    if isinstance(job, dict):
        if job.get("job_id"):
            return job_service.get_job(job["job_id"])
        return Job.from_dict(job)
    raise TypeError(f"Unsupported job type: {type(job)!r}")


def _resolve_style_json(job: Job, explicit_style_json: dict[str, Any] | None) -> dict[str, Any]:
    if explicit_style_json is not None:
        return explicit_style_json
    if job.style_json is not None:
        return job.style_json
    style_path = job.processing_config.get("style_json_path")
    if style_path:
        return json.loads(Path(style_path).read_text(encoding="utf-8"))
    raise ValueError(f"No style JSON available for job {job.job_id}")


def _ensure_style_json(
    *,
    style_data: dict[str, Any],
    work_dir: Path,
    existing_path: str | None,
) -> Path:
    if existing_path:
        existing = Path(existing_path)
        if existing.exists():
            return existing

    style_json_path = work_dir / "style.json"
    style_json_path.write_text(json.dumps(style_data, indent=2), encoding="utf-8")
    return style_json_path


def _resolve_render_config(processing_config: dict[str, Any]) -> dict[str, Any]:
    render_config = dict(processing_config.get("render", {}))
    for key in RENDER_CONFIG_KEYS:
        if key in processing_config and key not in render_config:
            render_config[key] = processing_config[key]
    return render_config


def _materialize_storage_asset(
    *,
    storage_path: str,
    fallback_name: str,
    destination_dir: Path,
) -> Path:
    path_text = storage_path.replace("file:///", "").replace("file://", "")
    local_path = Path(path_text)
    if storage_path.startswith("file://") and local_path.exists():
        return local_path

    storage_service = get_storage_service()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / fallback_name
    destination_path.write_bytes(storage_service.read_file(storage_path))
    return destination_path
