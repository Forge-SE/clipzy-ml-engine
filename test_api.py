"""
Example test script to verify the API and worker system.

Run this to test:
1. Upload a video
2. Create a job
3. Check job status
4. Get results

Make sure Redis and API server are running first!
"""

import time
import json
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"


def create_dummy_video(filename: str = "test_video.mp4", size_mb: int = 10) -> Path:
    """Create a dummy video file for testing."""
    path = Path(filename)
    # Create a minimal MP4-like file (not a real video, but passes basic validation)
    content = b"ftypisom" + b"\x00" * (size_mb * 1024 * 1024 - 8)
    path.write_bytes(content)
    print(f"Created test video: {filename} ({size_mb}MB)")
    return path


def test_health():
    """Test the health check endpoint."""
    print("\n1. Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_upload_video(filename: str = "test_video.mp4"):
    """Test video upload."""
    print("\n2. Testing video upload...")

    # Create dummy video
    video_path = create_dummy_video(filename, size_mb=1)

    try:
        with open(video_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{BASE_URL}/videos/upload",
                files=files
            )

        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")

        if response.status_code == 200:
            video_id = data["data"]["video_id"]
            print(f"\n✓ Video uploaded: {video_id}")
            return video_id
        else:
            print(f"\n✗ Upload failed: {data}")
            return None

    finally:
        # Cleanup
        video_path.unlink()


def test_create_job(video_id: str):
    """Test job creation."""
    print("\n3. Testing job creation...")

    payload = {
        "video_id": video_id,
        "template_video_id": None,
        "config": {"quality": "high"},
        "webhook_url": None
    }

    response = requests.post(
        f"{BASE_URL}/jobs",
        json=payload
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")

    if response.status_code == 200:
        job_id = data["data"]["job_id"]
        print(f"\n✓ Job created: {job_id}")
        return job_id
    else:
        print(f"\n✗ Job creation failed: {data}")
        return None


def test_get_job_status(job_id: str, max_retries: int = 30):
    """Poll job status until completion or timeout."""
    print(f"\n4. Polling job status (max {max_retries} retries)...")

    for i in range(max_retries):
        response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        data = response.json()

        if response.status_code == 200:
            job = data["data"]
            status = job["status"]
            progress = job["progress_percent"]
            stage = job.get("current_stage", "N/A")

            print(f"  [{i+1}] Status: {status} | Progress: {progress}% | Stage: {stage}")

            if status in ("completed", "failed", "cancelled"):
                print(f"\n✓ Job reached final state: {status}")
                return job

            time.sleep(2)
        else:
            print(f"  [{i+1}] Error: {response.status_code}")
            time.sleep(2)

    print("\n✗ Job did not complete within timeout")
    return None


def test_get_job_result(job_id: str):
    """Get job result with style JSON."""
    print(f"\n5. Getting job result...")

    response = requests.get(f"{BASE_URL}/jobs/{job_id}/result")
    data = response.json()

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        job = data["data"]
        style = job.get("style_json")

        print(f"✓ Result retrieved:")
        print(f"  - Status: {job['status']}")
        print(f"  - Progress: {job['progress_percent']}%")
        print(f"  - Processing time: {job.get('processing_time_seconds', 'N/A')}s")

        if style:
            print(f"\n  Style JSON sample:")
            print(f"    - Cut frequency: {style.get('cut_frequency')} cuts/min")
            print(f"    - Motion intensity: {style.get('motion_intensity')}%")
            print(f"    - Tempo: {style.get('tempo_bpm')} BPM")
            print(f"    - Genre: {style.get('music_genre')}")
            print(f"    - Color grade temp: {style.get('color_grade', {}).get('temperature')}°")

        if job.get("output_video_url"):
            print(f"\n  Output video: {job['output_video_url']}")

        return job
    else:
        print(f"✗ Failed to get result: {json.dumps(data, indent=2)}")
        return None


def test_list_jobs():
    """Test listing jobs."""
    print(f"\n6. Listing jobs...")

    response = requests.get(f"{BASE_URL}/jobs?page=1&page_size=10")
    data = response.json()

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        jobs_data = data["data"]
        print(f"✓ Retrieved {len(jobs_data['jobs'])} jobs (total: {jobs_data['total']})")
        return True
    else:
        print(f"✗ Failed to list jobs")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Clipzy API & Worker System Test")
    print("=" * 60)

    # Test health
    if not test_health():
        print("\n✗ API server is not running. Start it with: python main.py")
        return

    # Test video upload
    video_id = test_upload_video()
    if not video_id:
        print("\n✗ Video upload failed")
        return

    # Test job creation
    job_id = test_create_job(video_id)
    if not job_id:
        print("\n✗ Job creation failed")
        return

    # Wait for processing
    print("\n⏳ Waiting for job to complete...")
    print("   (Make sure a worker is running: python run_worker.py)")
    final_job = test_get_job_status(job_id)

    if final_job and final_job["status"] == "completed":
        # Get detailed result
        test_get_job_result(job_id)

    # List all jobs
    test_list_jobs()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to API server at localhost:8000")
        print("   Start the server with: python main.py")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
