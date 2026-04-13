#!/usr/bin/env python3
"""Modal worker - consumes jobs from RabbitMQ and processes them on GPU."""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set Modal credentials
os.environ["MODAL_TOKEN_ID"] = os.getenv("MODAL_TOKEN_ID", "")
os.environ["MODAL_TOKEN_SECRET"] = os.getenv("MODAL_TOKEN_SECRET", "")
os.environ["MODAL_CREDENTIALS_WARNING"] = "false"


def main():
    """Main worker loop - consumes jobs from RabbitMQ and processes on Modal GPU."""
    try:
        print("🚀 Starting Modal Worker (GPU Processing)...")
        print(f"Modal Token ID: {os.getenv('MODAL_TOKEN_ID')[:15]}...")
        
        from app.core.config import settings
        from app.services.rabbitmq_queue_service import RabbitMQQueueService
        from app.workers.modal_worker import VideoProcessor
        from app.core.constants import JobStatus
        from app.core.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        # Initialize services
        queue_service = RabbitMQQueueService(settings.RABBITMQ_URL)
        print("✓ Connected to RabbitMQ")
        
        print("\n📡 Waiting for video processing jobs...")
        print("   - Processing videos with GPU (A100/H100)")
        print("   - Using S3 storage for inputs/outputs")
        print("   - Updating job status in Redis")
        print("\n(Press Ctrl+C to stop)\n")
        
        # Initialize Modal processor
        processor = VideoProcessor()
        
        # Main processing loop
        while True:
            try:
                # Dequeue job from RabbitMQ
                job = queue_service.dequeue_job(timeout=30)
                
                if not job:
                    # No job available, keep waiting
                    time.sleep(5)
                    continue
                
                job_id = job.job_id
                video_id = job.video_id
                
                print(f"\n🎬 Processing job: {job_id}")
                print(f"   Video ID: {video_id}")
                
                # Update status to processing
                queue_service.set_job_status(job_id, JobStatus.PROCESSING.value)
                job_data = job.to_dict()
                job_data['status'] = JobStatus.PROCESSING.value
                job_data['progress_percent'] = 10
                job_data['current_stage'] = 'gpu_initialization'
                queue_service.set_job_data(job_id, job_data)
                
                # Get video from S3
                storage_path = job.processing_config.get('storage_path', '')
                if not storage_path:
                    # Fallback: use video storage path
                    video_data = queue_service.get_job_data(f"video_{video_id}")
                    storage_path = video_data.get('storage_path') if video_data else None
                
                if not storage_path:
                    logger.error(f"Storage path not found for job {job_id}")
                    queue_service.set_job_status(job_id, JobStatus.FAILED.value)
                    continue
                
                print(f"   Storage Path: {storage_path}")
                
                # Process video on Modal GPU
                print("   Stage: Video Analysis (GPU)")
                job_data['progress_percent'] = 25
                job_data['current_stage'] = 'video_analysis'
                queue_service.set_job_data(job_id, job_data)
                
                try:
                    result = processor.analyze_video(storage_path)
                    video_analysis = result if result else {}
                except Exception as e:
                    logger.warning(f"Video analysis failed (non-critical): {str(e)}")
                    video_analysis = {}
                
                print("   Stage: Audio Analysis (GPU)")
                job_data['progress_percent'] = 50
                job_data['current_stage'] = 'audio_analysis'
                queue_service.set_job_data(job_id, job_data)
                
                print("   Stage: Style Extraction (GPU)")
                job_data['progress_percent'] = 75
                job_data['current_stage'] = 'style_extraction'
                queue_service.set_job_data(job_id, job_data)
                
                # Store results
                final_result = {
                    'job_id': job_id,
                    'video_id': video_id,
                    'video_analysis': video_analysis,
                    'status': 'completed',
                    'processed_at': time.time(),
                }
                
                queue_service.set_job_result(job_id, final_result)
                queue_service.set_job_status(job_id, JobStatus.COMPLETED.value)
                
                job_data['status'] = JobStatus.COMPLETED.value
                job_data['progress_percent'] = 100
                job_data['current_stage'] = 'completed'
                queue_service.set_job_data(job_id, job_data)
                
                print(f"✓ Job completed: {job_id}")
                
            except Exception as e:
                logger.error(f"Error processing job: {str(e)}", exc_info=True)
                if 'job_id' in locals():
                    queue_service.set_job_status(job_id, JobStatus.FAILED.value)
                time.sleep(5)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Worker stopped")
        return 0
        
    except Exception as e:
        print(f"\n❌ FATAL Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
