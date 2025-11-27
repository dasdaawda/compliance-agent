# System Architecture

This document describes the architecture of the AI Compliance Agent platform, including components, data flow, resiliency measures, storage strategy, deployment topology, and supporting services.

## Table of Contents

1. [Overview](#overview)
2. [Component Diagram](#component-diagram)
3. [Core Components](#core-components)
4. [Data & Pipeline Flow](#data--pipeline-flow)
5. [Resiliency & Reliability](#resiliency--reliability)
6. [Storage Strategy](#storage-strategy)
7. [Notifications & Logging](#notifications--logging)
8. [Deployment Topology](#deployment-topology)
9. [External Integrations](#external-integrations)
10. [Operational Guides](#operational-guides)

---

## Overview

AI Compliance Agent is a "centaur" (AI + human operator) system that analyzes video content for compliance risks. It combines a Django monolith, Django REST Framework (DRF) API, an HTMX-based web interface, Celery workers, Redis, PostgreSQL, Backblaze B2 storage with Cloudflare CDN, and Replicate-hosted AI models.

Key characteristics:

- **Django 5 Application** with modular settings (`backend/compliance_app/settings/`)
- **REST API** served via DRF with JWT authentication
- **HTMX Frontend** for client dashboards and operator consoles
- **Celery Workers & Beat** orchestrating AI processing pipeline and periodic jobs
- **Redis** for Celery broker, caching signed URLs, and background job coordination
- **PostgreSQL** as the system of record (projects, videos, triggers, labels, pipeline metadata)
- **Backblaze B2 + Cloudflare** for durable object storage and low-cost CDN distribution
- **Replicate** for GPU-powered AI inference (Whisper, YOLO, NSFW/Violence detectors, OCR)

---

## Component Diagram

```
+-------------------+        +------------------+        +------------------+
|  Browser Clients  |<------>|    Django Web    |<------>|    PostgreSQL    |
| (Clients, Ops)    |        | (HTMX + DRF API) |        | (Relational DB)  |
+-------------------+        +------------------+        +------------------+
          ^                          ^       ^                       ^
          |                          |       |                       |
          | HTMX partials            |       | Celery tasks          |
          | Session auth             |       |                       |
          |                          |       |                       |
          |                          |       |                       |
          |                    +-----+-------+-----+
          |                    |     Celery Worker |
          |                    |  (Pipeline Steps) |
          |                    +----------+--------+
          |                               |
          |                               |
          |                +--------------v---------------+
          |                | Redis (Broker + Cache + TTL) |
          |                +--------------+---------------+
          |                               |
          |                               |
          |                    +----------v---------+
          |                    | Backblaze B2       |
          |                    | (Video Storage)    |
          |                    +----------+---------+
          |                               |
          |                 Cloudflare CDN |
          |                               v
          |                       Secure Video URLs
          |
          |                 +-------------------------+
          +-----------------| Replicate AI Endpoints |
                            +-------------------------+
```

---

## Core Components

### Django Web Layer
- Serves HTMX pages (`/client/*`) and DRF API endpoints (`/api/*`).
- Handles authentication (JWT + session), permission checks, and validation.
- Provides admin interfaces for operators and administrators.

### HTMX Frontend
- Session-authenticated dashboard for clients and operators.
- Uses HTMX to fetch partials for project lists, video uploads, pipeline statuses, and report modals.
- Integrates with Bootstrap 5 for UI consistency.

### DRF API
- JWT-authenticated API with endpoints for projects, videos, triggers, verification tasks, operator labels, pipeline executions, risk definitions, and user profiles.
- Auto-documented via DRF Spectacular with Swagger UI at `/api/docs/`.
- Enforces role-based permissions and owner scoping.

### Celery Workers
- Execute AI pipeline steps (validation, preprocessing, inference, report compilation).
- Handle background jobs such as artifact cleanup, CDN cache refresh, and notification dispatch.
- Configured with retries, backoff, and time limits for resiliency.

### Celery Beat
- Schedules periodic maintenance tasks (e.g., `cleanup_artifacts_periodic`, `refresh_cdn_cache_periodic`).

### Redis
- Serves as Celery broker and result backend.
- Caches signed B2 URLs (1-hour TTL) to reduce storage round-trips.
- Stores locking metadata for verification tasks and pipeline checkpoints.

### PostgreSQL
- Stores structured domain data: users, projects, videos, AI triggers, pipeline executions, verification tasks, operator labels, and audit logs.
- Uses JSONB columns for flexible AI reports and error traces.

### Backblaze B2 + Cloudflare
- Private B2 buckets store uploaded videos and AI artifacts.
- Cloudflare provides CDN acceleration and free egress when fronting B2.
- Signed URLs grant time-limited access to stored media.

### Replicate
- Hosts AI inference models (Whisper, YOLO, NSFW, Violent content detector, EasyOCR).
- Invoked from Celery tasks via authenticated API calls.

---

## Data & Pipeline Flow

### High-Level Flow

```
[Client Upload] --> [Video Validation] --> [Storage Upload] --> [AI Pipeline]
        |                    |                     |                |
        v                    v                     v                v
   Django/HTMX         VideoValidator         Backblaze B2      Celery Tasks
```

### Detailed Pipeline Steps

1. **Upload Initiation**
   - Client submits video via HTMX form or REST API (`POST /api/videos/`).
   - Django validates request, enforces file limits, and persists metadata.

2. **Pre-Processing & Storage**
   - Uploaded file is validated (`projects.validators.VideoValidator`).
   - Video stored in Backblaze B2 via `B2Utils` wrapper with retry logic and SHA256 checksum.
   - Entry created in `PipelineExecution` with status `pending`.

3. **AI Pipeline Execution** (Celery `run_full_pipeline` and sub-tasks)
   - **Preprocessing:** FPS normalization, audio extraction, frame sampling.
   - **Inference:** Calls Replicate models for ASR, object detection, NSFW/violence detection, OCR, and dictionary-based NLP checks.
   - **Trigger Generation:** Results persisted as `AITrigger` rows with metadata and risk codes.
   - **Report Compilation:** `ReportCompiler` aggregates AI results into `video.ai_report` JSON.

4. **Post-Processing**
   - `VerificationTask` generated for operator review when AI completes.
   - Videos move to `VERIFICATION` status until operator actions finish.
   - On verification completion, video status set to `COMPLETED`; summary stored in `decision_summary`.

5. **Operator Workflow**
   - Operators fetch pending tasks through API or HTMX views.
   - Tasks use optimistic locking with heartbeats (`VerificationTask.heartbeat`).
   - Operators create labels (`OperatorLabel`) referencing AI triggers.
   - Final decision updates `Video` and `PipelineExecution` statuses.

6. **Notifications**
   - Success: HTML email (`emails/video_ready.html`) to project owner.
   - Failure: Alerts to owner + admins via `notify_pipeline_failure`.

### Text Flow Diagram

```
Client Upload --> Django Validation --> Save Video + PipelineExecution -->
  Celery Queue --> Preprocess Media --> Replicate AI Calls --> Store AI Results -->
  Compile Report --> Create VerificationTask --> Operator Labels --> Final Decision --> Notifications
```

---

## Resiliency & Reliability

### Celery Task Resilience
- Each Celery task defines `autoretry_for`, `retry_backoff`, and timeouts.
- Tasks log structured events (`log_pipeline_step`) for observability.
- `run_full_pipeline` is idempotent: it reads `PipelineExecution` state to resume after crashes.

### PipelineExecution Tracking
- Fields `status`, `current_task`, `progress`, `last_step`, `retry_count`, and `error_trace` capture exact pipeline position and failure context.
- `error_trace` stores chronological JSON entries for post-mortem analysis.
- `retry_count` increments automatically when tasks retry, enabling alerting when thresholds are exceeded.

### Backblaze Resilience
- `storage/b2_utils.py` wraps B2 operations with tenacity-based retries and exponential backoff.
- Signed URL generation is cached in Redis and invalidated upon deletion to avoid stale links.
- Artifact cleanup tasks enforce retention policies (7 days for completed pipelines, 14 days for failed ones, 24 hours for temporary media).

### Validation Safeguards
- `VideoValidator` ensures file size, duration, and format meet configured limits before pipeline execution.
- Duplicate detection via SHA256 prevents redundant processing.
- Balance checks ensure users have sufficient credits before consuming compute resources.

---

## Storage Strategy

| Data Type | Storage | Notes |
|-----------|---------|-------|
| Video files, frames, extracted audio | **Backblaze B2** | Private bucket, signed URLs via Cloudflare, artifacts auto-cleaned |
| AI reports, metadata | **PostgreSQL (JSONB)** | `video.ai_report`, `PipelineExecution.error_trace` |
| Temporary files | **Local disk (`/tmp`)** | Cleaned after pipeline completion |
| Signed URLs | **Redis** | 1-hour TTL cache for B2 signed URLs |
| Operator logs/history | **PostgreSQL** | `OperatorActionLog`, `OperatorLabel` |

**Retention Policies:**
- Completed video artifacts deleted after 7 days to reduce storage costs.
- Failed pipelines retained for 14 days to aid debugging.
- Temporary preprocessing files deleted within 24 hours.

**Security:**
- B2 buckets remain private; only signed URLs grant access.
- Cloudflare CDN configured as a front door for B2 to reduce egress costs and enforce TLS.

---

## Notifications & Logging

### Notifications
- `send_video_ready_notification` dispatches HTML emails to clients once AI + operator review is complete.
- `notify_pipeline_failure` sends alerts containing video ID, failed stage, and error message to admins and project owners.
- Email backend configured via environment variables (see [CONFIGURATION.md](CONFIGURATION.md)).

### Logging
- Structured JSON logging from pipeline tasks includes `video_id`, `step`, `status`, and error details for centralized log ingestion.
- Django application logs capture API requests, authentication events, and system warnings.
- Celery logs aggregated via Docker Compose or external log collectors.

### Monitoring Suggestions
- Track pipeline durations, retry counts, and error traces via PostgreSQL metrics.
- Leverage DigitalOcean logs, Cloudflare analytics, and Backblaze usage reports for infrastructure observability.

---

## Deployment Topology

### Docker Compose Stack (Local & Staging)

| Service | Description |
|---------|-------------|
| `web` | Django + Gunicorn application server |
| `celery-worker` | Celery worker processing AI tasks |
| `celery-beat` | Scheduler for periodic jobs |
| `postgres` | PostgreSQL database |
| `redis` | Message broker + cache |
| `minio` | Local S3-compatible storage for development |

**Entrypoint Script:** `scripts/entrypoint.sh` ensures the DB is ready, runs migrations, collects static files, and starts Gunicorn.

**Production Deployment:**
- Typically deployed to DigitalOcean App Platform or Kubernetes with managed PostgreSQL and Redis.
- Dockerfile includes multi-stage build, non-root user, and health checks.
- See [DEPLOYMENT.md](../DEPLOYMENT.md) for detailed instructions, environment variable templates, and troubleshooting.

### Network Considerations
- Web service exposes port 8000 (HTTPS terminated at load balancer/CDN).
- Celery worker communicates with Redis and PostgreSQL within the private network.
- All outbound AI calls go over HTTPS to Replicate endpoints.
- Backblaze B2 endpoints configured via environment variables; Cloudflare CDN handles public distribution.

---

## External Integrations

| Service | Purpose | Integration Notes |
|---------|---------|-------------------|
| **Replicate** | AI inference (Whisper, YOLO, NSFW, Violence, OCR, NLP) | Auth via `REPLICATE_API_TOKEN` environment variable. Requests made from Celery tasks only. |
| **Backblaze B2** | Durable object storage | Credentials stored in environment variables. Access through `B2Utils` wrapper with retries. |
| **Cloudflare CDN** | Edge caching, free B2 egress | Optional but recommended. Configure CNAME pointing to B2 friendly URL and use API tokens for cache purges. |
| **Email provider** (SendGrid, Gmail, SES) | Notifications | Configured via Django email settings (`EMAIL_HOST`, `EMAIL_PORT`, etc.). |

---

## Operational Guides

- **Configuration Reference:** [CONFIGURATION.md](CONFIGURATION.md)
- **Deployment Guide:** [DEPLOYMENT.md](../DEPLOYMENT.md)
- **API Usage:** [API.md](API.md)
- **Pipeline Resilience & Storage:** See sections in [CONFIGURATION.md](CONFIGURATION.md)
- **Docker Quickstart:** [DOCKER_QUICKSTART.md](../DOCKER_QUICKSTART.md)

For troubleshooting and escalation paths, refer to the respective guides above.
