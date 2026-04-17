#!/usr/bin/env python3
"""Direct Modal worker runner - bypasses CLI circular import issue"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set Modal credentials
os.environ["MODAL_TOKEN_ID"] = os.getenv("MODAL_TOKEN_ID", "")
os.environ["MODAL_TOKEN_SECRET"] = os.getenv("MODAL_TOKEN_SECRET", "")
os.environ["MODAL_CREDENTIALS_WARNING"] = "false"

def main():
    """Run Modal worker"""
    try:
        print("🚀 Starting Modal GPU Worker...")
        print(f"Token ID: {os.getenv('MODAL_TOKEN_ID')[:15]}...")
        
        # Import and run the worker
        from app.workers.modal_worker import process_job
        
        # Example usage
        print("\n📝 Modal Worker is ready for GPU processing!")
        print("\nUsage in your code:")
        print('  from app.workers.modal_worker import VideoProcessor')
        print('  processor = VideoProcessor()')
        print('  result = processor.analyze_video.remote("s3://...")')
        print("\nOr submit a job via API:")
        print("  curl -X POST http://localhost:8000/api/v1/jobs")
        
        return 0
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nTry installing dotenv:")
        print("  pip install python-dotenv")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
