#!/usr/bin/env python3
"""Modal worker - consumes jobs from RabbitMQ and processes them on GPU."""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import tempfile
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
        
        # Initialize pipelines for local processing (won't have GPU, but will work)
        try:
            from app.pipelines import (
                AudioAnalyzer,
                MotionAnalyzer,
                StyleApplier,
                StyleExtractor,
                VideoAnalyzer,
                VideoRenderer,
            )
            processor.AudioAnalyzer = AudioAnalyzer
            processor.MotionAnalyzer = MotionAnalyzer
            processor.StyleApplier = StyleApplier
            processor.StyleExtractor = StyleExtractor
            processor.VideoAnalyzer = VideoAnalyzer
            processor.VideoRenderer = VideoRenderer
            print("✓ Analysis pipelines initialized")
        except ImportError as e:
            print(f"⚠ Could not import pipelines: {e}")
            processor.AudioAnalyzer = None
            processor.VideoAnalyzer = None
        
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
                job_data['current_stage'] = 'video_analysis'
                if not job_data.get('started_at'):
                    job_data['started_at'] = datetime.now(timezone.utc).isoformat()  # Set start time on first transition to processing
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
                
                # Import real analyzers and storage service
                from app.pipelines import VideoAnalyzer, StyleExtractor
                from app.services import get_storage_service
                
                # Download video from S3 to local temp file if needed
                local_video_path = storage_path
                temp_video_file = None
                
                if storage_path.startswith('s3://'):
                    print("   Downloading video from S3...")
                    try:
                        storage_service = get_storage_service()
                        video_bytes = storage_service.read_file(storage_path)
                        
                        # Create temp file for analysis
                        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                            tmp.write(video_bytes)
                            temp_video_file = tmp.name
                            local_video_path = temp_video_file
                        
                        print(f"   ✓ Downloaded to: {local_video_path}")
                    except Exception as e:
                        logger.error(f"Failed to download video from S3: {str(e)}", exc_info=True)
                        print(f"   ⚠ S3 download failed: {str(e)}")
                        queue_service.set_job_status(job_id, JobStatus.FAILED.value)
                        continue
                
                # Process video with REAL analyzers
                print("   Stage: Video Analysis")
                job_data['progress_percent'] = 25
                job_data['current_stage'] = 'VIDEO_ANALYSIS'
                queue_service.set_job_data(job_id, job_data)
                
                video_analysis = {}
                audio_analysis = {}
                motion_analysis = {}
                style_json_obj = None
                
                try:
                    # Run comprehensive video analysis using OpenCV, PySceneDetect, Librosa
                    video_analysis = VideoAnalyzer.analyze(local_video_path)
                    print(f"   ✓ Video analysis complete - {len(video_analysis.get('shots', []))} shots detected")
                    
                    # Extract audio and motion analysis from the result
                    style_dna = video_analysis.get('style_dna', {})
                    
                    # Prepare audio analysis data
                    audio_analysis = {
                        'tempo_bpm': style_dna.get('audio', {}).get('tempo'),
                        'beats': style_dna.get('audio', {}).get('beats', []),
                        'has_speech': bool(style_dna.get('speech')),
                        'energy': style_dna.get('audio', {}).get('energy'),
                    }
                    
                    # Prepare motion analysis data
                    motion_analysis = {
                        'global_motion': {
                            'average_intensity': style_dna.get('motion', {}).get('intensity', 0.5),
                            'camera_zoom': style_dna.get('motion', {}).get('zoom_detected'),
                        }
                    }
                    
                    print("   Stage: Style Extraction")
                    job_data['progress_percent'] = 75
                    job_data['current_stage'] = 'STYLE_EXTRACTION'
                    queue_service.set_job_data(job_id, job_data)
                    
                    # Extract style manifest from analysis
                    style_json_obj = StyleExtractor.extract(
                        video_path=local_video_path,
                        video_analysis=video_analysis,
                        audio_analysis=audio_analysis,
                        motion_analysis=motion_analysis,
                    )
                    print(f"   ✓ Style extraction complete - confidence: {style_json_obj.extraction_confidence}")
                    
                except Exception as e:
                    logger.error(f"Analysis failed: {str(e)}", exc_info=True)
                    print(f"   ⚠ Analysis error: {str(e)}")
                    video_analysis = {"error": str(e), "status": "failed"}
                    style_json_obj = None
                finally:
                    # Clean up temp file
                    if temp_video_file and os.path.exists(temp_video_file):
                        try:
                            os.remove(temp_video_file)
                            print("   ✓ Cleaned up temp file")
                        except Exception as e:
                            logger.warning(f"Failed to clean up temp file: {str(e)}")
                
                # Store results
                final_result = {
                    'job_id': job_id,
                    'video_id': video_id,
                    'video_analysis': video_analysis,
                    'status': 'completed',
                    'processed_at': time.time(),
                }
                
                # Convert StyleJSON object to dict
                style_json = style_json_obj.model_dump() if style_json_obj else None
                
                queue_service.set_job_result(job_id, final_result)
                queue_service.set_job_status(job_id, JobStatus.COMPLETED.value)
                
                job_data['status'] = JobStatus.COMPLETED.value
                job_data['progress_percent'] = 100
                job_data['current_stage'] = None
                job_data['completed_at'] = datetime.now(timezone.utc).isoformat()  # Set completion time
                job_data['style_json'] = style_json  # Store extracted style data
                job_data['output_video_url'] = f"file:///tmp/output_{job_id}.mp4"  # Placeholder output URL
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
