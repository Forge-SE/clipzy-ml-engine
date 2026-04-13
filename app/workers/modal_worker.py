"""Modal GPU worker for distributed video processing."""

import modal
import os
from pathlib import Path

# Create Modal app (updated to use modal.App instead of deprecated modal.Stub)
app = modal.App("clipzy-video-processing")

# Define image with required dependencies
image = (
    modal.Image.debian_slim()
    .pip_install(
        "fastapi==0.104.1",
        "opencv-python==4.8.0.76",
        "librosa==0.10.0",
        "openai-whisper==20230117",
        "transformers==4.36.2",
        "torch==2.1.1",
        "soundfile==0.12.1",
        "Pillow==10.1.0",
        "scikit-image==0.22.0",
        "numpy==1.26.2",
        "pandas==2.1.3",
        "scipy==1.11.4",
        "boto3==1.34.0",
        "pika==1.3.2",
        "redis==5.0.1",
        "pydantic==2.5.0",
        "pydantic-settings==2.1.0",
    )
)


@app.cls(image=image, gpu="A100", timeout=3600)
class VideoProcessor:
    """GPU-accelerated video processor on Modal."""

    @modal.enter()
    def setup(self):
        """Initialize processor on GPU."""
        # Import here to avoid issues on local machine
        from app.pipelines import (
            AudioAnalyzer,
            MotionAnalyzer,
            StyleApplier,
            StyleExtractor,
            VideoAnalyzer,
            VideoRenderer,
        )
        self.AudioAnalyzer = AudioAnalyzer
        self.MotionAnalyzer = MotionAnalyzer
        self.StyleApplier = StyleApplier
        self.StyleExtractor = StyleExtractor
        self.VideoAnalyzer = VideoAnalyzer
        self.VideoRenderer = VideoRenderer

    
    def analyze_video(self, video_path: str) -> dict:
        """
        Analyze video on GPU.

        Args:
            video_path: Path to video file (local or S3)

        Returns:
            Analysis results
        """
        from app.core.logging_config import get_logger

        logger = get_logger(__name__)
        logger.info(f"Starting video analysis on Modal GPU", extra={"video_path": video_path})

        # Download from S3 if needed
        if video_path.startswith("s3://"):
            video_path = self._download_from_s3(video_path)

        results = {
            "video_analysis": self.VideoAnalyzer.analyze(video_path),
            "audio_analysis": self.AudioAnalyzer.analyze(video_path),
            "motion_analysis": self.MotionAnalyzer.analyze(video_path),
        }

        logger.info("Video analysis completed on Modal GPU")
        return results

    
    def extract_style(self, template_path: str) -> dict:
        """
        Extract style from template video on GPU.

        Args:
            template_path: Path to template video

        Returns:
            Style information
        """
        from app.core.logging_config import get_logger

        logger = get_logger(__name__)
        logger.info(f"Starting style extraction on Modal GPU", extra={"template_path": template_path})

        if template_path.startswith("s3://"):
            template_path = self._download_from_s3(template_path)

        style = self.StyleExtractor.extract(template_path)

        logger.info("Style extraction completed on Modal GPU")
        return style

    
    def apply_style(self, source_video: str, style_data: dict, output_path: str) -> str:
        """
        Apply style to video on GPU.

        Args:
            source_video: Source video path
            style_data: Style information
            output_path: Output file path

        Returns:
            Output file path
        """
        from app.core.logging_config import get_logger

        logger = get_logger(__name__)
        logger.info(f"Starting style application on Modal GPU")

        if source_video.startswith("s3://"):
            source_video = self._download_from_s3(source_video)

        styled_video = self.StyleApplier.apply(source_video, style_data)

        # Save to local and upload to S3
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        styled_video.save(output_path)

        logger.info("Style application completed on Modal GPU")
        return output_path

    
    def render_video(self, video_data: dict, effects: list, output_path: str) -> str:
        """
        Render final video with effects on GPU.

        Args:
            video_data: Video data
            effects: List of effects to apply
            output_path: Output file path

        Returns:
            Output file path
        """
        from app.core.logging_config import get_logger

        logger = get_logger(__name__)
        logger.info(f"Starting video rendering on Modal GPU")

        output = self.VideoRenderer.render(video_data, effects)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        output.save(output_path)

        logger.info("Video rendering completed on Modal GPU")
        return output_path

    @staticmethod
    def _download_from_s3(s3_path: str) -> str:
        """Download file from S3 to local storage."""
        import boto3
        from app.core.config import settings

        s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        # Parse S3 path
        parts = s3_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]

        # Download to temp location
        local_path = f"/tmp/{Path(key).name}"
        s3_client.download_file(bucket, key, local_path)

        return local_path


@app.local_entrypoint()
def process_job(job_id: str, video_path: str, template_path: str = None):
    """
    Process a video job using Modal GPU.

    Args:
        job_id: Job ID
        video_path: Path to video
        template_path: Optional template video path
    """
    from app.services import get_job_service, get_storage_service
    from app.core.constants import JobStatus, ProcessingStage
    from app.core.logging_config import get_logger

    logger = get_logger(__name__)
    job_service = get_job_service()
    storage_service = get_storage_service()

    processor = VideoProcessor()

    try:
        logger.info(f"Processing job on Modal", extra={"job_id": job_id})

        # Step 1: Analyze video
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=5,
            stage=ProcessingStage.VIDEO_ANALYSIS
        )

        analysis = processor.analyze_video.remote(video_path)
        job_service.update_job_progress(
            job_id,
            JobStatus.PROCESSING,
            progress_percent=40,
            stage=ProcessingStage.AUDIO_ANALYSIS
        )

        # Step 2: Extract style if template provided
        style = None
        if template_path:
            style = processor.extract_style.remote(template_path)
            job_service.update_job_progress(
                job_id,
                JobStatus.PROCESSING,
                progress_percent=60,
                stage=ProcessingStage.STYLE_EXTRACTION
            )

        # Step 3: Apply style
        if style:
            styled_video = processor.apply_style.remote(video_path, style, f"/tmp/styled_{job_id}.mp4")
            job_service.update_job_progress(
                job_id,
                JobStatus.PROCESSING,
                progress_percent=80,
                stage=ProcessingStage.STYLE_APPLICATION
            )

        # Step 4: Save results
        output_path = f"{job_id}_output.mp4"
        storage_service.save_file(Path("/tmp/styled_" + job_id + ".mp4"), job_id)

        job_service.update_job_progress(
            job_id,
            JobStatus.COMPLETED,
            progress_percent=100,
            stage=ProcessingStage.COMPLETED
        )

        logger.info(f"Job processing completed on Modal", extra={"job_id": job_id})

    except Exception as e:
        logger.error(f"Job processing failed on Modal: {str(e)}", extra={"job_id": job_id})
        job_service.update_job_progress(
            job_id,
            JobStatus.FAILED,
            progress_percent=0,
            error=str(e)
        )
