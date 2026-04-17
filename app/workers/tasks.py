"""Background worker tasks for video processing."""

import traceback
from pathlib import Path

from app.core.constants import JobStatus, ProcessingStage
from app.core.logging_config import get_logger
from app.pipelines import (
    AudioAnalyzer,
    MotionAnalyzer,
    StyleExtractor,
    VideoAnalyzer,
    run_style_and_render,
)
from app.services import get_job_service

logger = get_logger(__name__)


def process_video_job(job_id: str) -> None:
    """
    Main task to process a video job through the complete pipeline.

    This is called by the worker and orchestrates the entire processing flow:
    1. Video Analysis
    2. Audio Analysis
    3. Motion Analysis
    4. Style Extraction
    5. Style Application
    6. Rendering

    Args:
        job_id: ID of the job to process
    """
    job_service = get_job_service()

    logger.info(f"Starting video processing job", extra={"job_id": job_id})
    failed_stage = ProcessingStage.VIDEO_ANALYSIS

    try:
        # Get job details
        job = job_service.get_job(job_id)
        video = job_service.get_video(job.video_id)

        if not video:
            raise ValueError(f"Video not found: {job.video_id}")

        # Get actual file path from storage URL
        video_path = Path(video.storage_path.replace("file:///", "").replace("file://", ""))

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Mark as processing
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=5,
            stage=ProcessingStage.VIDEO_ANALYSIS
        )

        # Step 1: Video Analysis
        failed_stage = ProcessingStage.VIDEO_ANALYSIS
        logger.info(f"Stage: Video Analysis", extra={"job_id": job_id})
        video_analysis = VideoAnalyzer.analyze(str(video_path))
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=20,
            stage=ProcessingStage.VIDEO_ANALYSIS
        )

        # Step 2: Audio Analysis
        failed_stage = ProcessingStage.AUDIO_ANALYSIS
        logger.info(f"Stage: Audio Analysis", extra={"job_id": job_id})
        audio_analysis = AudioAnalyzer.analyze(str(video_path))
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=35,
            stage=ProcessingStage.AUDIO_ANALYSIS
        )

        # Step 3: Motion Analysis
        failed_stage = ProcessingStage.MOTION_ANALYSIS
        logger.info(f"Stage: Motion Analysis", extra={"job_id": job_id})
        motion_analysis = MotionAnalyzer.analyze(str(video_path))
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=50,
            stage=ProcessingStage.MOTION_ANALYSIS
        )

        # Step 4: Style Extraction
        failed_stage = ProcessingStage.STYLE_EXTRACTION
        logger.info(f"Stage: Style Extraction", extra={"job_id": job_id})
        template_path = str(video_path)  # Use source video as template if none provided
        if job.template_video_id:
            template_video = job_service.get_video(job.template_video_id)
            if template_video:
                template_path = template_video.storage_path.replace("file:///", "").replace("file://", "")

        style_json = StyleExtractor.extract(
            video_path=template_path,
            video_analysis=video_analysis,
            audio_analysis=audio_analysis,
            motion_analysis=motion_analysis,
        )

        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=65,
            stage=ProcessingStage.STYLE_EXTRACTION
        )
        job_service.set_job_result(job_id, style_json=style_json.model_dump())

        # Step 5/6: Style transfer + rendering
        failed_stage = ProcessingStage.STYLE_TRANSFER
        logger.info(f"Stage: Style Transfer + Rendering", extra={"job_id": job_id})
        run_style_and_render(job_service.get_job(job_id), style_json=style_json.model_dump())

        logger.info(f"Job completed successfully", extra={"job_id": job_id})

    except Exception as e:
        current_stage = failed_stage
        try:
            current_stage = job_service.get_job(job_id).current_stage or failed_stage
        except Exception:
            current_stage = failed_stage

        logger.error(
            f"Job processing failed: {str(e)}",
            extra={"job_id": job_id, "error": str(e), "traceback": traceback.format_exc()}
        )

        # Mark as failed
        job_service.set_job_error(
            job_id,
            error_message=str(e),
            stage=current_stage,
            details={"traceback": traceback.format_exc()}
        )
