# API Documentation

This document describes the REST API and HTMX interfaces for the AI Compliance Agent system.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [API Documentation Tools](#api-documentation-tools)
5. [API Resources](#api-resources)
6. [Query Parameters & Filtering](#query-parameters--filtering)
7. [Sample Requests & Responses](#sample-requests--responses)
8. [Status & Error Codes](#status--error-codes)
9. [Pagination](#pagination)
10. [File Uploads](#file-uploads)
11. [HTMX Interface](#htmx-interface)
12. [Rate Limiting & Security](#rate-limiting--security)

---

## Overview

The system provides two complementary interfaces:

- **REST API** (`/api/*`) - JSON responses for programmatic access
  - JWT token-based authentication
  - Suitable for external integrations, mobile apps, and automation
  
- **HTMX Interface** (`/client/*`) - Server-rendered HTML partials
  - Django session authentication
  - Optimized for web browser interactions with minimal JavaScript
  - CSRF protection enabled

---

## Authentication

### JWT Authentication (REST API)

**Obtain Token**

```http
POST /api/auth/token/
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "your_password"
}
```

**Response:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Refresh Token**

```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Token Lifetimes:**
- Access token: 1 hour
- Refresh token: 7 days

**Usage:**

Include the access token in the `Authorization` header for all API requests:

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Session Authentication (HTMX)

Standard Django session-based authentication:

- Login: `POST /client/users/login/`
- Logout: `POST /client/users/logout/`
- CSRF token required for all POST/PUT/DELETE requests
- Session cookie automatically managed by browser

### Role-Based Permissions

The system implements three user roles with specific permissions:

| Role | Description | Access |
|------|-------------|--------|
| **CLIENT** | Content creators/video uploaders | Own projects, videos, reports |
| **OPERATOR** | Content moderators | Verification tasks, labeling |
| **ADMIN** | System administrators | All resources, user management |

**Permission Classes** (`users/permissions.py`):
- `IsClient` - Restricts access to CLIENT role
- `IsOperator` - Restricts access to OPERATOR role
- `IsAdmin` - Restricts access to ADMIN role
- `IsProjectOwner` - Allows access only to owned resources
- `IsTaskAssignee` - Allows access only to assigned tasks

---

## Base URLs

**Production:**
```
https://yourdomain.com/api/
https://yourdomain.com/client/
```

**Development (Docker Compose):**
```
http://localhost:8000/api/
http://localhost:8000/client/
```

---

## API Documentation Tools

### Swagger UI (Interactive)

**URL:** `/api/docs/`

Interactive API documentation with "Try it out" functionality. Explore all endpoints, view request/response schemas, and test API calls directly from the browser.

### OpenAPI Schema

**URL:** `/api/schema/`

Download the OpenAPI 3.0 schema in JSON format for use with code generators, testing tools, or custom documentation.

---

## API Resources

### Projects (`/api/projects/`)

Manage video projects and groupings.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/projects/` | List user's projects | IsClient |
| POST | `/api/projects/` | Create new project | IsClient |
| GET | `/api/projects/{id}/` | Get project details | IsProjectOwner |
| PUT | `/api/projects/{id}/` | Update project | IsProjectOwner |
| PATCH | `/api/projects/{id}/` | Partial update | IsProjectOwner |
| DELETE | `/api/projects/{id}/` | Delete project | IsProjectOwner |
| GET | `/api/projects/{id}/videos/` | List project videos | IsProjectOwner |
| GET | `/api/projects/{id}/statistics/` | Get project stats | IsProjectOwner |

#### Filters & Search
- **Search:** `?search=project_name`
- **Ordering:** `?ordering=-created_at`, `?ordering=name`

---

### Videos (`/api/videos/`)

Upload, manage, and process video content.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/videos/` | List user's videos | IsClient |
| POST | `/api/videos/` | Upload new video | IsClient |
| GET | `/api/videos/{id}/` | Get video details | IsProjectOwner |
| DELETE | `/api/videos/{id}/` | Delete video | IsProjectOwner |
| GET | `/api/videos/{id}/signed-url/` | Get streaming URL | IsProjectOwner |
| GET | `/api/videos/{id}/report/` | Get AI report | IsProjectOwner |
| POST | `/api/videos/{id}/retry-processing/` | Retry failed job | IsProjectOwner |

#### Filters & Search
- **Filter by status:** `?status=PROCESSING`, `?status=COMPLETED`, `?status=FAILED`
- **Filter by project:** `?project={project_id}`
- **Search:** `?search=video_name`
- **Ordering:** `?ordering=-created_at`, `?ordering=duration`, `?ordering=file_size`

#### Video Statuses
- `UPLOADED` - Video uploaded, awaiting processing
- `PROCESSING` - AI pipeline in progress
- `VERIFICATION` - AI complete, awaiting operator verification
- `COMPLETED` - Verification complete
- `FAILED` - Processing failed

---

### AI Triggers (`/api/triggers/`)

View AI-detected potential compliance issues.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/triggers/` | List triggers | IsAuthenticated |
| GET | `/api/triggers/{id}/` | Get trigger details | IsAuthenticated |

#### Filters
- **Filter by video:** `?video={video_id}`
- **Filter by source:** `?trigger_source=whisper_profanity`, `?trigger_source=yolo_object`
- **Filter by status:** `?status=pending`, `?status=processed`

#### Trigger Sources
- `whisper_profanity` - Profanity detected via Whisper ASR
- `whisper_brand` - Brand mention detected
- `falconsai_nsfw` - NSFW content detected
- `violence_detector` - Violence/gore detected
- `yolo_object` - Prohibited object detected (weapons, drugs, etc.)
- `easyocr_text` - Prohibited text detected via OCR

---

### Verification Tasks (`/api/verification-tasks/`)

Operator workflow for reviewing AI triggers.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/verification-tasks/` | List all tasks | IsOperator/IsAdmin |
| GET | `/api/verification-tasks/pending/` | List available tasks | IsOperator |
| GET | `/api/verification-tasks/my_tasks/` | List assigned tasks | IsOperator |
| POST | `/api/verification-tasks/{id}/assign/` | Assign task to self | IsOperator |
| POST | `/api/verification-tasks/{id}/heartbeat/` | Update lock | IsTaskAssignee |
| POST | `/api/verification-tasks/{id}/complete/` | Complete task | IsTaskAssignee |
| POST | `/api/verification-tasks/{id}/release/` | Release lock | IsTaskAssignee |

#### Task Workflow

1. **Fetch pending tasks:** `GET /api/verification-tasks/pending/`
2. **Assign to self:** `POST /api/verification-tasks/{id}/assign/`
3. **Periodic heartbeat:** `POST /api/verification-tasks/{id}/heartbeat/` (every 5-10 minutes)
4. **Complete or release:** `POST /api/verification-tasks/{id}/complete/` or `release/`

**Task Locking:**
- Tasks are locked for 2 hours when assigned
- Heartbeat extends lock by 1 hour
- Stale locks automatically expire

---

### Operator Labels (`/api/operator-labels/`)

Manual labels applied by operators to AI triggers.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/operator-labels/` | List labels | IsOperator |
| POST | `/api/operator-labels/` | Create label | IsOperator |
| GET | `/api/operator-labels/{id}/` | Get label details | IsOperator |
| PUT | `/api/operator-labels/{id}/` | Update label | IsOperator |
| DELETE | `/api/operator-labels/{id}/` | Delete label | IsOperator |
| GET | `/api/operator-labels/my_labels/` | List own labels | IsOperator |
| GET | `/api/operator-labels/statistics/` | Label statistics | IsOperator |

#### Label Types
- `ok_true` - Confirmed violation (true positive)
- `ok_false` - False alarm (false positive)
- `skip` - Inconclusive/skipped
- `escalate` - Escalated to admin review

---

### Pipeline Executions (`/api/pipeline-executions/`)

View AI processing pipeline status and history.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/pipeline-executions/` | List executions | IsAuthenticated |
| GET | `/api/pipeline-executions/{id}/` | Get execution details | IsAuthenticated |

#### Execution Statuses
- `pending` - Pipeline queued
- `running` - Processing in progress
- `completed` - Successfully finished
- `failed` - Pipeline failed (see `error_trace`)

---

### Risk Definitions (`/api/risk-definitions/`)

Reference data for compliance risk types.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/risk-definitions/` | List risk definitions | IsAuthenticated |
| GET | `/api/risk-definitions/{id}/` | Get risk details | IsAuthenticated |

#### Risk Levels
- `low` - Minor issue
- `medium` - Moderate risk
- `high` - Critical violation

---

### Users (`/api/users/`)

User profile and account management.

#### Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/users/me/` | Get current user profile | IsAuthenticated |
| PUT | `/api/users/me/update_profile/` | Update profile | IsAuthenticated |
| GET | `/api/users/balance/` | Get balance info | IsClient |

---

## Query Parameters & Filtering

### Common Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `page` | Page number for pagination | `?page=2` |
| `page_size` | Items per page (max 100) | `?page_size=50` |
| `search` | Full-text search | `?search=keyword` |
| `ordering` | Sort results | `?ordering=-created_at` |

### Ordering

Prefix field names with `-` for descending order:

```
?ordering=created_at      # Ascending
?ordering=-created_at     # Descending
?ordering=name,-created_at  # Multiple fields
```

### Filtering

Use exact field matches:

```
?status=PROCESSING
?project=550e8400-e29b-41d4-a716-446655440000
?trigger_source=whisper_profanity
```

---

## Sample Requests & Responses

### Create Project

**Request:**

```http
POST /api/projects/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Marketing Campaign Q1",
  "description": "Video review for Q1 marketing materials"
}
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Marketing Campaign Q1",
  "description": "Video review for Q1 marketing materials",
  "owner": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Upload Video

**Request:**

```http
POST /api/videos/
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

project: 550e8400-e29b-41d4-a716-446655440000
original_name: Interview Video Final Cut
video_file: <binary data>
```

**Response (201 Created):**

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "project": "550e8400-e29b-41d4-a716-446655440000",
  "original_name": "Interview Video Final Cut",
  "status": "UPLOADED",
  "status_message": "",
  "file_size": 104857600,
  "duration": 180,
  "checksum_sha256": "a3b2c1d4e5f6...",
  "created_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### Get Signed Video URL

**Request:**

```http
GET /api/videos/7c9e6679-7425-40de-944b-e07fc1f90ae7/signed-url/
Authorization: Bearer {access_token}
```

**Response (200 OK):**

```json
{
  "signed_url": "https://s3.us-west-000.backblazeb2.com/ai-compliance-videos/...",
  "expires_in": 3600
}
```

### Get AI Report

**Request:**

```http
GET /api/videos/7c9e6679-7425-40de-944b-e07fc1f90ae7/report/
Authorization: Bearer {access_token}
```

**Response (200 OK):**

```json
{
  "video_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "processing_completed_at": "2024-01-15T10:45:00Z",
  "summary": {
    "total_triggers": 5,
    "by_source": {
      "whisper_profanity": 2,
      "falconsai_nsfw": 1,
      "yolo_object": 2
    },
    "risk_level": "medium"
  },
  "triggers": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "timestamp_sec": 45.5,
      "trigger_source": "whisper_profanity",
      "confidence": 0.95,
      "data": {
        "text": "profane word detected",
        "language": "ru"
      }
    }
  ]
}
```

### Create Operator Label

**Request:**

```http
POST /api/operator-labels/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "video": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "ai_trigger": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "start_time_sec": 45.5,
  "final_label": "ok_false",
  "comment": "False positive - speaker quoting prohibited content in educational context"
}
```

**Response (201 Created):**

```json
{
  "id": "9f8e7d6c-5b4a-3210-fedc-ba0987654321",
  "video": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "ai_trigger": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "operator": "operator@example.com",
  "start_time_sec": 45.5,
  "final_label": "ok_false",
  "comment": "False positive - speaker quoting prohibited content in educational context",
  "created_at": "2024-01-15T11:00:00Z"
}
```

---

## Status & Error Codes

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Successful GET/PUT/PATCH request |
| 201 | Created | Successful POST request |
| 204 | No Content | Successful DELETE request |
| 400 | Bad Request | Invalid input, validation error |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource, state conflict |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Maintenance or overload |

### Error Response Format

```json
{
  "error": "Validation failed",
  "detail": "File size exceeds maximum allowed size (2GB)",
  "code": "file_too_large"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `authentication_failed` | Invalid or expired token |
| `permission_denied` | User lacks required role/permission |
| `not_found` | Resource not found |
| `validation_error` | Input validation failed |
| `file_too_large` | File exceeds `MAX_VIDEO_FILE_SIZE` |
| `invalid_format` | Unsupported video format |
| `duplicate_file` | File already uploaded (checksum match) |
| `insufficient_balance` | User lacks credits for processing |
| `task_locked` | Verification task locked by another operator |
| `pipeline_error` | AI processing pipeline failure |

---

## Pagination

API list endpoints use cursor-based pagination by default.

### Request

```http
GET /api/videos/?page=2&page_size=20
```

### Response

```json
{
  "count": 157,
  "next": "http://localhost:8000/api/videos/?page=3",
  "previous": "http://localhost:8000/api/videos/?page=1",
  "results": [
    {
      "id": "...",
      "original_name": "Video 1"
    }
  ]
}
```

### Parameters

- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

---

## File Uploads

### Video Upload Constraints

| Constraint | Value | Setting |
|------------|-------|---------|
| **Max file size** | 2 GB | `MAX_VIDEO_FILE_SIZE` |
| **Max duration** | 2 hours | `MAX_VIDEO_DURATION` |
| **Allowed formats** | mp4, avi, mov, mkv, webm | `ALLOWED_VIDEO_FORMATS` |

### Upload Process

1. **Client validates file** (size, format) before upload
2. **POST multipart/form-data** to `/api/videos/`
3. **Server validates file** (size, format, duration)
4. **Calculate SHA256 checksum** for duplicate detection
5. **Check user balance** (sufficient processing minutes)
6. **Upload to B2 storage** with retry logic
7. **Trigger AI pipeline** (Celery task)
8. **Return video object** with `status=UPLOADED`

### Duplicate Detection

The system calculates SHA256 checksums to prevent duplicate uploads within the same project. If a duplicate is detected:

```json
{
  "error": "Duplicate video",
  "detail": "A video with the same content already exists in this project",
  "code": "duplicate_file",
  "existing_video_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

### Signed URLs

All video streaming URLs are temporary signed URLs:

- **Expiration:** 1 hour (3600 seconds)
- **Caching:** Redis cache (1 hour TTL)
- **Security:** No direct B2 credentials exposure

**Request signed URL:**

```http
GET /api/videos/{id}/signed-url/
```

**Response:**

```json
{
  "signed_url": "https://...",
  "expires_in": 3600
}
```

**Usage in video player:**

```html
<video src="https://..." controls></video>
```

---

## HTMX Interface

The HTMX interface provides server-rendered HTML partials for browser-based interactions.

### Dashboard

**URL:** `/client/dashboard/`

Main client dashboard with project overview, statistics, and quick actions.

### HTMX Patterns

#### Project List (Auto-Refresh)

```html
<div id="projects-list"
     hx-get="/client/htmx/projects/"
     hx-trigger="load, projectCreated from:body"
     hx-swap="innerHTML">
</div>
```

#### Create Project (Modal Form)

```html
<button hx-get="/client/htmx/projects/create/"
        hx-target="#modal-content"
        data-bs-toggle="modal"
        data-bs-target="#actionModal">
  Create Project
</button>
```

#### Upload Video

```html
<form hx-post="/client/htmx/projects/{id}/upload/"
      hx-target="#videos-list"
      hx-encoding="multipart/form-data">
  {% csrf_token %}
  <input type="text" name="original_name" required />
  <input type="file" name="video_file" accept="video/*" required />
  <button type="submit">Upload</button>
</form>
```

### HTMX Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /client/htmx/projects/` | Project list partial |
| `GET /client/htmx/projects/create/` | Project form |
| `POST /client/htmx/projects/create/` | Submit project |
| `GET /client/htmx/projects/{id}/videos/` | Video list |
| `GET /client/htmx/projects/{id}/upload/` | Upload form |
| `POST /client/htmx/projects/{id}/upload/` | Submit video |
| `GET /client/htmx/videos/{id}/report/` | Report modal |
| `GET /client/htmx/videos/{id}/signed-url/` | Video player |

### CSRF Protection

All HTMX POST/PUT/DELETE requests must include CSRF token:

```html
<form hx-post="..." hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
  {% csrf_token %}
  ...
</form>
```

---

## Rate Limiting & Security

### Recommended Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/auth/token/` | 5 requests/minute |
| `/api/videos/` (POST) | 10 uploads/hour |
| `/api/*` (GET) | 100 requests/minute |
| `/api/*` (POST/PUT/DELETE) | 60 requests/minute |

**Note:** Rate limiting is not enforced by default. Consider adding DRF throttling classes in production.

### Security Best Practices

1. **Always use HTTPS** in production
2. **Rotate JWT tokens** regularly
3. **Validate file uploads** on both client and server
4. **Set CORS policies** if accessing API from different domains
5. **Monitor API usage** for unusual patterns
6. **Enable rate limiting** to prevent abuse
7. **Use secure B2 signed URLs** - never expose B2 credentials to clients

---

## Additional Resources

- **Configuration Guide:** See [CONFIGURATION.md](CONFIGURATION.md)
- **Deployment Guide:** See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture Overview:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Interactive API Docs:** `/api/docs/` (Swagger UI)
- **OpenAPI Schema:** `/api/schema/`

---

## Support

For issues or questions:
1. Check Swagger UI at `/api/docs/` for live examples
2. Review error messages and status codes above
3. Consult [CONFIGURATION.md](CONFIGURATION.md) for settings
4. See [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
