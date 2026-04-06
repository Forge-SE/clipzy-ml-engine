"""Background worker tasks for video processing."""

import traceback
from pathlib import Path

from app.core.constants import JobStatus, ProcessingStage
from app.core.logging_config import get_logger
from app.pipelines import (
    AudioAnalyzer,
    MotionAnalyzer,
    StyleApplier,
    StyleExtractor,
    VideoAnalyzer,
    VideoRenderer,
)
from app.services import get_job_service, get_storage_service

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
    storage_service = get_storage_service()

    logger.info(f"Starting video processing job", extra={"job_id": job_id})

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
        logger.info(f"Stage: Video Analysis", extra={"job_id": job_id})
        video_analysis = VideoAnalyzer.analyze(str(video_path))
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=20,
            stage=ProcessingStage.VIDEO_ANALYSIS
        )

        # Step 2: Audio Analysis
        logger.info(f"Stage: Audio Analysis", extra={"job_id": job_id})
        audio_analysis = AudioAnalyzer.analyze(str(video_path))
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=35,
            stage=ProcessingStage.AUDIO_ANALYSIS
        )

        # Step 3: Motion Analysis
        logger.info(f"Stage: Motion Analysis", extra={"job_id": job_id})
        motion_analysis = MotionAnalyzer.analyze(str(video_path))
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=50,
            stage=ProcessingStage.MOTION_ANALYSIS
        )

        # Step 4: Style Extraction
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

        # Step 5: Style Application
        logger.info(f"Stage: Style Application", extra={"job_id": job_id})
        output_applied_path = str(video_path).replace(".mp4", "_styled.mp4")
        style_application_result = StyleApplier.apply(
            input_video_path=str(video_path),
            style=style_json,
            output_path=output_applied_path,
        )
        
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=80,
            stage=ProcessingStage.STYLE_APPLICATION
        )

        # Step 6: Rendering
        logger.info(f"Stage: Rendering", extra={"job_id": job_id})
        job_folder = f"job_{job_id}"
        output_filename = f"{job_id}_output.mp4"
        
        # For this stub, we'll just save to storage folder
        render_result = VideoRenderer.render(
            video_path=output_applied_path,
            output_path=str(Path(video_path).parent / output_filename),
            quality="high",
        )

        # Store output in storage service
        output_storage_path = storage_service.save_file(
            Path(render_result["output_video_path"]),
            job_folder
        )

        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=95,
            stage=ProcessingStage.RENDERING
        )

        # Mark as completed
        job_service.set_job_result(
            job_id,
            style_json=style_json.model_dump(),
            output_video_url=output_storage_path,
        )

        job_service.update_job_progress(
            job_id,
            JobStatus.COMPLETED,
            progress_percent=100,
            stage=ProcessingStage.RENDERING
        )

        logger.info(f"Job completed successfully", extra={"job_id": job_id})

    except Exception as e:
        logger.error(
            f"Job processing failed: {str(e)}",
            extra={"job_id": job_id, "error": str(e), "traceback": traceback.format_exc()}
        )

        # Mark as failed
        job_service.set_job_error(
            job_id,
            error_message=str(e),
            stage=ProcessingStage.STYLE_EXTRACTION,
            details={"traceback": traceback.format_exc()}
        )
