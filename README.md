# Clipzy: AI-Powered Video Processing Backend

A production-ready FastAPI backend for automated video processing and AI-driven video editing. Built for scalability, extensibility, and GPU-heavy workloads.

## Overview

Clipzy processes videos through an intelligent pipeline:

1. **Video Analysis** - Extract cuts, pacing, composition, motion
2. **Audio Analysis** - Detect speech, music, beats, tempo
3. **Motion Analysis** - Track camera movement and object motion
4. **Style Extraction** - Generate style manifesto from template video
5. **Style Application** - Apply extracted style to user footage
6. **Rendering** - Produce final optimized video output

## Project Structure

```
clipzy-infra/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/      # API route handlers
│   │   │   │   ├── health.py
│   │   │   │   ├── videos.py
│   │   │   │   └── jobs.py
│   │   │   └── router.py
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py           # Settings & environment config
│   │   ├── constants.py         # App-wide constants
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── logging_config.py    # Structured logging setup
│   ├── models/                  # Data models (dataclasses)
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic layer
│   │   ├── job_service.py       # Job orchestration
│   │   ├── queue_service.py     # Redis queue management
│   │   └── storage_service.py   # File storage abstraction
│   ├── pipelines/               # Video processing modules
│   │   ├── video_analysis.py
│   │   ├── audio_analysis.py
│   │   ├── motion_analysis.py
│   │   ├── style_extraction.py
│   │   ├── style_application.py
│   │   └── rendering.py
│   ├── workers/                 # Background job processor
│   │   ├── video_worker.py
│   │   └── tasks.py
│   ├── utils/                   # Utility functions
│   └── main.py                  # FastAPI app factory
├── storage/                      # Local video storage (created at runtime)
├── main.py                       # Application entry point
├── run_worker.py                 # Worker script
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables
├── .env.example                  # Example env file
├── docker-compose.yml            # Redis + dev services
└── README.md                     # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Redis (Docker)

```bash
docker-compose up -d
```

Or install Redis locally and run it:

```bash
redis-server
```

### 3. Run the API Server

```bash
python main.py
```

API will be available at `http://localhost:8000`

Swagger docs: `http://localhost:8000/docs`

### 4. Run a Worker (in another terminal)

```bash
python run_worker.py --worker-id worker-1
```

Run multiple workers for parallelism:

```bash
python run_worker.py --worker-id worker-1 &
python run_worker.py --worker-id worker-2 &
python run_worker.py --worker-id worker-3 &
```

## API Endpoints

### Health Check

```http
GET /api/v1/health
```

### Upload Video

```http
POST /api/v1/videos/upload

Content-Type: multipart/form-data

file: <video file>
template_video_id: (optional)
webhook_url: (optional)
```

**Response:**
```json
{
  "success": true,
  "message": "Video uploaded successfully",
  "data": {
    "video_id": "vid_abc123",
    "filename": "my_video.mp4",
    "file_size_bytes": 52428800,
    "metadata": {
      "width": 1920,
      "height": 1080,
      "duration_seconds": 60.0,
      "frame_rate": 30.0,
      "codec": "h264",
      "bitrate_kbps": 5000,
      "format": "mp4"
    },
    "uploaded_at": "2024-04-05T10:30:00Z",
    "storage_url": "file:///storage/vid_abc123/my_video.mp4"
  }
}
```

### Create Job

```http
POST /api/v1/jobs

{
  "video_id": "vid_abc123",
  "template_video_id": null,
  "config": {"quality": "high"},
  "webhook_url": "https://example.com/webhook"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Job created",
  "data": {
    "job_id": "job_xyz789",
    "video_id": "vid_abc123",
    "status": "queued",
    "progress_percent": 0,
    "current_stage": null,
    "created_at": "2024-04-05T10:30:00Z",
    "updated_at": "2024-04-05T10:30:00Z"
  }
}
```

### Get Job Status

```http
GET /api/v1/jobs/{job_id}
```

**Response: Same as above with updated status/progress**

### Get Job Result (with Style JSON)

```http
GET /api/v1/jobs/{job_id}/result
```

**Response:**
```json
{
  "success": true,
  "message": "Job result retrieved",
  "data": {
    "job_id": "job_xyz789",
    "status": "completed",
    "progress_percent": 100,
    "style_json": {
      "version": "1.0",
      "color_grade": {...},
      "cut_frequency": 3.5,
      "motion_intensity": 65,
      ...
    },
    "output_video_url": "file:///storage/job_xyz789/output.mp4",
    "processing_time_seconds": 900.0
  }
}
```

### List Jobs

```http
GET /api/v1/jobs?page=1&page_size=10
```

## Configuration

All configuration is managed via environment variables in `.env`:

```env
# Environment
ENV=dev                          # dev, prod, test
DEBUG=true

# API
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["*"]

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
STORAGE_TYPE=local              # local or s3
LOCAL_STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=1000

# Processing
PROCESSING_TIMEOUT_SECONDS=3600
MAX_CONCURRENT_JOBS=5

# Logging
LOG_LEVEL=INFO
```

## Architecture

### Layers

**API Layer** (`app/api/`)
- RESTful endpoints with versioning
- Request validation with Pydantic
- Standardized response format

**Services Layer** (`app/services/`)
- `JobService` - Job lifecycle management
- `QueueService` - Redis queue operations
- `StorageService` - File storage abstraction

**Pipeline Layer** (`app/pipelines/`)
- Modular processing stages
- Each can be replaced with real implementations
- Stub implementations provided for quick testing

**Workers** (`app/workers/`)
- Background job processor
- Pulls jobs from Redis queue
- Orchestrates pipeline stages
- Handles errors and retries

### Data Flow

```
Upload Video
    ↓
Create Job
    ↓
Enqueue to Redis
    ↓
Worker picks up job
    ↓
Video Analysis → Audio Analysis → Motion Analysis
    ↓
Style Extraction
    ↓
Style Application
    ↓
Rendering
    ↓
Store Result + Notify (webhook)
```

## Style JSON Schema

The `StyleJSON` model defines the extracted style manifesto:

```python
{
  "version": "1.0",
  
  # Visual Style
  "color_grade": {
    "temperature": 10,
    "tint": 5,
    "saturation": 20,
    "contrast": 15,
    "highlights": 10,
    "shadows": -5
  },
  "aspect_ratio": "16:9",
  "frame_rate": 30,
  
  # Audio Style
  "audio_style": {
    "normalization_level": 0.85,
    "compression_ratio": 4.0,
    "bass_boost": 20,
    "enhance_speech": true
  },
  
  # Pacing & Motion
  "cut_frequency": 3.5,
  "motion_intensity": 65,
  "zoom_usage": 30,
  
  # Transitions
  "primary_transition": {
    "type": "fade",
    "duration_ms": 300,
    "easing": "ease-in-out"
  },
  
  # Beat Sync
  "detected_beats": [
    {
      "timestamp_ms": 0,
      "confidence": 0.95,
      "frequency": "bass"
    }
  ],
  "tempo_bpm": 120.0,
  "music_genre": "pop",
  
  # Metadata
  "created_at": "2024-04-05T10:30:00Z",
  "source_duration_seconds": 60.0,
  "extraction_confidence": 0.92
}
```

## Testing the System

### 1. Upload a Video

```bash
curl -X POST "http://localhost:8000/api/v1/videos/upload" \
  -F "file=@sample_video.mp4"
```

Returns: `video_id`, `job_id`

### 2. Check Job Status

```bash
curl "http://localhost:8000/api/v1/jobs/job_xyz789"
```

### 3. Get Results (when completed)

```bash
curl "http://localhost:8000/api/v1/jobs/job_xyz789/result"
```

Returns: Style JSON, output video URL, processing time

## Scaling & Production

### Database
Replace in-memory storage with PostgreSQL:
- Replace `JobService._jobs_store` with SQLAlchemy models
- Use connection pooling (psycopg2 + pooling)

### Workers
- Run workers in separate containers/processes
- Use Kubernetes for orchestration
- Scale based on queue size

### Storage
Replace local storage with S3:
```python
self.storage_type = "s3"
# Use boto3 for S3 operations
```

### Monitoring
Add Prometheus metrics:
```python
from prometheus_client import Counter, Histogram

job_processed = Counter(...)
processing_duration = Histogram(...)
```



## Error Handling

All errors follow this format:

```json
{
  "success": false,
  "message": "Descriptive error message",
  "error": {
    "detail": "Technical details",
    "code": "ERROR_CODE"
  }
}
```

Structured logging captures all operations:
```json
{
  "timestamp": "2024-04-05T10:30:00.000000",
  "level": "INFO",
  "logger": "app.services.job_service",
  "message": "Job created",
  "job_id": "job_xyz789",
  "video_id": "vid_abc123"
}
```

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

### With Multiple Workers

Terminal 1: API Server
```bash
python main.py
```

Terminal 2-4: Workers
```bash
python run_worker.py --worker-id worker-1
python run_worker.py --worker-id worker-2
python run_worker.py --worker-id worker-3
```

## Environment-Specific Configuration

### Development

```env
ENV=dev
DEBUG=true
LOG_LEVEL=DEBUG
CORS_ORIGINS=["*"]
```

### Production

```env
ENV=prod
DEBUG=false
LOG_LEVEL=WARNING
CORS_ORIGINS=["https://app.clipzy.com"]
REDIS_URL=redis://redis-prod:6379/0
STORAGE_TYPE=s3


## License

Proprietary - Forge Studios & Clipzy AI Video Processing

## Support

For issues or questions, please refer to the documentation or contact the development team.
