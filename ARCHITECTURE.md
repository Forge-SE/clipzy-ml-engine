# System Architecture Overview

## High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENT/USER                             │
│                 (Web Browser, Mobile App, etc.)                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTP Requests
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI WEB SERVER                            │
│                    (main.py - Port 8000)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              API Endpoints (app/api/v1/)                │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  GET  /health                  → Health Check           │   │
│  │  POST /videos/upload           → Upload Video           │   │
│  │  POST /jobs                    → Create Job             │   │
│  │  GET  /jobs/{id}               → Get Job Status         │   │
│  │  GET  /jobs/{id}/result        → Get Results + Style    │   │
│  │  GET  /jobs                    → List All Jobs          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Services Layer (app/services/)              │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  • JobService        → Job lifecycle management         │   │
│  │  • QueueService      → Redis queue operations           │   │
│  │  • StorageService    → File storage abstraction         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Request Validation & Response Formatting         │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────┬──────────────────────────────┘
                       │          │
        ┌──────────────┘          └──────────────┐
        │                                        │
        ↓                                        ↓
┌─────────────────┐                    ┌──────────────────┐
│  REDIS QUEUE    │                    │  STORAGE LAYER   │
│  (Port 6379)    │                    │  (./storage/)    │
├─────────────────┤                    ├──────────────────┤
│                 │                    │                  │
│ Job Queue:      │                    │ Videos:          │
│ ┌─────────────┐ │                    │ ┌──────────────┐ │
│ │ job_xyz789  │ │                    │ │ vid_abc123   │ │
│ │ job_def456  │ │                    │ │ vid_ghi789   │ │
│ └─────────────┘ │                    │ └──────────────┘ │
│                 │                    │                  │
│ Job Data:       │                    │ Outputs:         │
│ ┌─────────────┐ │                    │ ┌──────────────┐ │
│ │ Key: Status │ │                    │ │ job_*/output │ │
│ │ Results     │ │                    │ └──────────────┘ │
│ └─────────────┘ │                    │                  │
└────┬────────────┘                    └──────────────────┘
     │
     │ Dequeue Jobs
     │
     ↓
┌──────────────────────────────────────────────────────────┐
│          BACKGROUND WORKERS (run_worker.py)             │
│          (Multiple instances, polling queue)             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Worker Process 1: job_xyz789                           │
│  ┌────────────────────────────────────────────────────┐ │
│  │                                                    │ │
│  │  ↓ Pick Job from Queue                            │ │
│  │  ↓                                                 │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │    app/pipelines/ (6-Stage Processing)      │ │ │
│  │  ├──────────────────────────────────────────────┤ │ │
│  │  │ 1. Video Analysis        → Extract shots     │ │ │
│  │  │ 2. Audio Analysis        → Beats, speech     │ │ │
│  │  │ 3. Motion Analysis       → Camera/objects    │ │ │
│  │  │ 4. Style Extraction      → Generate Style.JSON│ │ │
│  │  │ 5. Style Application     → Apply to footage  │ │ │
│  │  │ 6. Rendering             → Final output      │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  │  ↓                                                 │ │
│  │  ↓ Store Results in Redis & Storage              │ │
│  │                                                    │ │
│  │  Status: COMPLETED                                │ │
│  │  Style JSON: {...}                                │ │
│  │  Output URL: file:///storage/...                  │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Worker Process 2: Waiting for jobs...                 │
│  Worker Process 3: Waiting for jobs...                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Request Flow: Video Upload → Processing → Results

```
USER                    API                    SERVICE              QUEUE              WORKER            STORAGE
│                       │                        │                    │                   │                 │
├──POST /upload video───→│                        │                    │                   │                 │
│                        │                        │                    │                   │                 │
│                        ├─Validate video────────→│                    │                   │                 │
│                        │<─Return video_id───────┤                    │                   │                 │
│                        │                        │                    │                   │                 │
│                        ├─Create job────────────→│                    │                   │                 │
│                        │                        ├─Enqueue to Redis──→│                   │                 │
│                        │                        │                    │                   │                 │
│←──Response: video_id──┤                        │                    │                   │                 │
│   job_id              │                        │                    │                   │                 │
│                       │                        │                    ├─Poll queue───────→│                 │
│                       │                        │                    │<─Found job────────┤                 │
│                       │                        │                    │                    │                 │
│                       │                        │                    │                    ├─Download video─→│
│                       │                        │                    │                    │<─File content───┤
│                       │                        │                    │                    │                 │
│                       │                        │                    │                    ├─Video Analysis──┤
│                       │                        │                    │                    ├─Audio Analysis──┤
│                       │                        │                    │                    ├─Motion Analysis─┤
│                       │                        │                    │                    ├─Style Extract───┤
│                       │                        │                    │                    ├─Style Apply─────┤
│                       │                        │                    │                    ├─Rendering───────┤
│                       │                        │                    │                    │                 │
│──GET /jobs/{id}──────→│                        │                    │                    │                 │
│                       ├─Get job status────────→│                    │                    │                 │
│                       │                        ├─Query Redis──────→│                    │                 │
│←─Status: processing───┤                        │<─Return status────┤                    │                 │
│   progress: 45%       │                        │                   │                    │                 │
│                       │                        │                    │                    ├─Update results─→│
│                       │                        │                    │                    ├─Store output───→│
│                       │                        │                    │                    │                 │
│──GET /jobs/{id}/result│                        │                   │                    │                 │
│                       ├─Get full result───────→│                   │                    │                 │
│                       │                        ├─Query Redis──────→│                    │                 │
│←─Style JSON───────────┤                        │<─Return results───┤                    │                 │
│ output_video_url      │                        │                   │                    │                 │
│ processing_time       │                        │                   │                    │                 │
│                       │                        │                   │                    │                 │
```

---

## Architecture Patterns

### 1. Services Pattern
```python
# Endpoints call services
endpoint.upload() → JobService.create_job()
endpoint.get_status() → JobService.get_job()

# Services manage business logic
JobService.create_job() → QueueService.enqueue()
```

### 2. Dependency Injection
```python
# Services are injected into endpoints
job_service = get_job_service()
queue_service = get_queue_service()
storage_service = get_storage_service()

# All use Redis connection pool
```

### 3. Data Flow Through Layers
```
API Request
    ↓
Pydantic Validation (schemas)
    ↓
Service Logic (services)
    ↓
Queue/Storage Operations
    ↓
Pydantic Response Model
    ↓
HTTP JSON Response
```

### 4. Worker Pattern
```
Worker
    ↓
Dequeue Job from Redis
    ↓
Load Job Data
    ↓
Execute Pipeline Stages
    ↓
Update Progress in Redis
    ↓
Store Results
    ↓
Poll for Next Job
    ↓
(Infinite Loop)
```

---

## Component Interaction Matrix

```
┌─────────────────┬──────────┬──────────┬─────────┬──────────┐
│ Component       │ API      │ Services │ Schemas │ Pipelines│
├─────────────────┼──────────┼──────────┼─────────┼──────────┤
│ API Endpoints   │ ▌ USES   │ ▌ CALLS  │ ▌ USES  │          │
│ Services        │          │ ▌ IMPL   │ ▌ USES  │ ▌ CALLS  │
│ Schemas         │          │          │ ▌ REUSE │          │
│ Pipelines       │          │          │ ▌ USES  │ ▌ CHAINS │
│ Workers         │          │ ▌ CALLS  │ ▌ USES  │ ▌ CALLS  │
│ Redis           │          │ ▌ USES   │         │          │
│ Storage         │          │ ▌ USES   │         │          │
└─────────────────┴──────────┴──────────┴─────────┴──────────┘
```

---

## Data Model Relationships

```
┌──────────────┐                    ┌──────────────┐
│    Video     │                    │     Job      │
├──────────────┤                    ├──────────────┤
│ video_id     │◄──belongs_to────┐  │ job_id       │
│ filename     │                  └──│ video_id     │
│ file_size    │                    │ status       │
│ metadata     │                    │ progress     │
│ storage_path │                    │ style_json   │
│ created_at   │                    │ output_url   │
└──────────────┘                    │ created_at   │
                                    │ completed_at │
                                    └──────────────┘
                                           │
                                           ├─ uses style_json
                                           ├─ tracks progress
                                           └─ stores in Redis
```

---

## Environment Map

```
Development Environment
├── App: localhost:8000 (FastAPI)
├── Redis: localhost:6379
├── Storage: ./storage/ (local filesystem)
├── Workers: 1-3 processes (polling)
└── Logs: console (JSON format)

Production Environment
├── App: Load-balanced instances
├── Redis: Redis Cluster (HA)
├── Storage: S3 bucket with CDN
├── Workers: Kubernetes pods (autoscaled)
└── Logs: Centralized logging (CloudWatch/ELK)
```

---

## Execution Timeline

```
T=0s    User uploads video
        → API validates
        → Create job (status: queued)
        → Enqueue to Redis

T=1s    Worker picks up job
        → Update status: processing
        
T=2-5s  Video Analysis
        → progress: 0-20%
        
T=6-10s Audio Analysis
        → progress: 20-35%
        
T=11-15s Motion Analysis
        → progress: 35-50%
        
T=16-20s Style Extraction
        → progress: 50-65%
        
T=21-25s Style Application
        → progress: 65-80%
        
T=26-30s Rendering
        → progress: 80-100%
        
T=31s   Job Complete
        → status: completed
        → style_json populated
        → output_video_url set
        
T=32+s  User queries results
        → GET /jobs/{id}/result
        → Returns complete data
```

---

## Error Handling Flow

```
Error Occurs (any stage)
    │
    ├─ Log with context
    │  (job_id, stage, error message)
    │
    ├─ Set job.error field
    │
    ├─ Update job status: FAILED
    │
    ├─ Store in Redis
    │
    └─ Return error in API response
       (status: 500, message, details)
```

---

## Scaling Architecture

### Current (Single Worker)
```
API Server
    ↓
Redis Queue
    ↓
Worker (1)
```

### Scalable (Multiple Workers)
```
Load Balancer
    ↓
API Servers (N)
    ↓
Redis Queue
    ↓
Workers (M) ← Can scale independently
```

### Production (Kubernetes)
```
Kubernetes Cluster
├── API Pod (Replicas: 3)
├── Redis Pod
└── Worker Pods (Replicas: Auto-scale based on queue depth)
```

---

## Key Design Decisions

✅ **Redis for Queue**: Simple, fast, reliable pub/sub  
✅ **In-Memory Storage (Dev)**: Easy to replace with DB  
✅ **Local File Storage (Dev)**: Easy to replace with S3  
✅ **Modular Pipelines**: Each stage independent  
✅ **Service Layer**: Separation of concerns  
✅ **Type Hints**: IDE support + safety  
✅ **Pydantic Models**: Request/response validation  
✅ **Structured Logging**: JSON format for aggregation  
✅ **Custom Exceptions**: Clear error handling  

---

This architecture ensures:
- **Scalability** - Workers can be added horizontally
- **Extensibility** - Components can be swapped
- **Maintainability** - Clear separation of concerns
- **Reliability** - Error handling at every layer
- **Performance** - Async/await, queue system
