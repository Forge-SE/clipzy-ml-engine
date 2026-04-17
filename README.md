# Clipzy Infrastructure

**Clipzy** is a video analysis and style extraction platform that automatically analyzes video content and generates cinematic styles for creative enhancement.

## What We've Built

### Core Components

- **FastAPI REST API** - Endpoints for video uploads, job management, health checks, and result retrieval
- **Video Analysis Pipeline** - 6-stage processing system:
  1. Video Analysis (shot detection, visual embeddings, color analysis)
  2. Audio Analysis (speech recognition, beat detection)
  3. Motion Analysis (camera movement, object detection)
  4. Style Extraction (generates style.json with cinematography recommendations)
  5. Style Application (applies extracted styles to footage)
  6. Rendering (produces final output video)

- **Background Worker System** - Queue-based job processing with Redis for distributing analysis tasks
- **Job Management Service** - Tracks job lifecycle from upload through completion
- **Storage Layer** - Handles video uploads and output storage
- **Modal Integration** - Support for distributed processing via Modal.com workers

### Architecture

The system follows a producer-consumer pattern:
- Users upload videos via API → Jobs are queued in Redis
- Background workers poll queue and process videos through the 6-stage pipeline
- Results (style JSON, output videos) stored and retrieved via API

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system diagrams and request flows.

### Tech Stack

- **Backend**: Python, FastAPI, Pydantic
- **Queue**: Redis
- **Processing**: OpenCV, Audio analysis libraries
- **Worker**: Python workers + Modal.com integration
- **Storage**: Local file system

---

[Full Documentation](https://personal-30a7f38f.mintlify.app/introduction)
