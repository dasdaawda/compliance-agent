# API & HTMX Implementation Documentation

## Overview

This document describes the REST API and HTMX implementation for the AI Compliance Agent system. The implementation provides two interfaces:
- **REST API** (`/api/...`) - JSON responses for programmatic access with JWT authentication
- **HTMX Interface** (`/client/...`) - Server-rendered HTML partials with session authentication

## Architecture

### Authentication

#### JWT Authentication (API)
- **Endpoint**: `POST /api/auth/token/`
- **Request**: `{"username": "user@example.com", "password": "password"}`
- **Response**: `{"access": "token...", "refresh": "token..."}`
- **Usage**: Include `Authorization: Bearer <access_token>` header in API requests

#### Session Authentication (HTMX)
- Standard Django session authentication
- CSRF protection enabled for all POST/PUT/DELETE requests
- Login via `/client/users/login/`

### Role-Based Permissions

#### Permission Classes (`users/permissions.py`)

1. **IsClient** - Allows only users with CLIENT role
2. **IsOperator** - Allows only users with OPERATOR role
3. **IsAdmin** - Allows only users with ADMIN role
4. **IsProjectOwner** - Allows access only to owned resources
5. **IsTaskAssignee** - Allows access only to assigned verification tasks

### API Endpoints

#### Projects (`/api/projects/`)

**List/Create Projects**
- `GET /api/projects/` - List user's projects (paginated)
- `POST /api/projects/` - Create new project
  ```json
  {
    "name": "Project Name",
    "description": "Optional description"
  }
  ```

**Project Details**
- `GET /api/projects/{id}/` - Get project details
- `PUT /api/projects/{id}/` - Update project
- `DELETE /api/projects/{id}/` - Delete project

**Project Actions**
- `GET /api/projects/{id}/videos/` - List project videos
- `GET /api/projects/{id}/statistics/` - Get project statistics

#### Videos (`/api/videos/`)

**List/Upload Videos**
- `GET /api/videos/` - List user's videos (paginated, filterable)
  - Filters: `?status=PROCESSING`, `?project={id}`
- `POST /api/videos/` - Upload new video (multipart/form-data)
  ```json
  {
    "project": "uuid",
    "original_name": "Video Title",
    "video_file": "<file>"
  }
  ```

**Video Details**
- `GET /api/videos/{id}/` - Get video details
- `DELETE /api/videos/{id}/` - Delete video

**Video Actions**
- `GET /api/videos/{id}/signed-url/` - Get signed streaming URL
  ```json
  {
    "signed_url": "https://...",
    "expires_in": 3600
  }
  ```
- `GET /api/videos/{id}/report/` - Get AI analysis report
- `POST /api/videos/{id}/retry-processing/` - Retry failed processing

#### AI Triggers (`/api/triggers/`)

**List Triggers**
- `GET /api/triggers/` - List AI triggers (role-filtered)
  - Filters: `?video={id}`, `?trigger_source=whisper_profanity`, `?status=pending`

#### Verification Tasks (`/api/verification-tasks/`)

**Operator Endpoints**
- `GET /api/verification-tasks/pending/` - List available tasks
- `GET /api/verification-tasks/my_tasks/` - List operator's assigned tasks
- `POST /api/verification-tasks/{id}/assign/` - Assign task to self
- `POST /api/verification-tasks/{id}/heartbeat/` - Update task lock
- `POST /api/verification-tasks/{id}/complete/` - Complete task
  ```json
  {
    "decision_summary": "All triggers reviewed and labeled"
  }
  ```
- `POST /api/verification-tasks/{id}/release/` - Release task lock

#### Operator Labels (`/api/operator-labels/`)

**Label Management**
- `GET /api/operator-labels/` - List labels (operator-filtered)
- `POST /api/operator-labels/` - Create new label
  ```json
  {
    "video": "uuid",
    "ai_trigger": "uuid",
    "start_time_sec": 10.5,
    "final_label": "ok_false",
    "comment": "False positive - no violation"
  }
  ```
- `GET /api/operator-labels/my_labels/` - List operator's labels
- `GET /api/operator-labels/statistics/` - Get label statistics

#### Users (`/api/users/`)

**User Management**
- `GET /api/users/me/` - Get current user profile
- `PUT /api/users/me/update_profile/` - Update profile
- `GET /api/users/balance/` - Get balance information

### HTMX Interface

#### Dashboard (`/client/dashboard/`)

Main client dashboard with project overview and statistics.

**Features:**
- Real-time statistics (projects, videos, processing status)
- HTMX-powered project list with auto-refresh
- Modal-based project creation and video upload
- No full page reloads

#### HTMX Partials

**Project Partials**
- `GET /client/htmx/projects/` - Project list partial
- `GET /client/htmx/projects/create/` - Project creation form
- `POST /client/htmx/projects/create/` - Submit project (returns updated list)

**Video Partials**
- `GET /client/htmx/projects/{id}/videos/` - Video list for project
- `GET /client/htmx/projects/{id}/upload/` - Video upload form
- `POST /client/htmx/projects/{id}/upload/` - Submit video (returns updated list)

**Report Partials**
- `GET /client/htmx/videos/{id}/report/` - Video report modal content
- `GET /client/htmx/videos/{id}/signed-url/` - Video player with signed URL

### Validation & Security

#### File Upload Validation

**Video Upload Restrictions:**
- **Max Size**: 2 GB (configurable via `MAX_VIDEO_FILE_SIZE`)
- **Allowed Formats**: MP4, AVI, MOV, MKV, WEBM (configurable via `ALLOWED_VIDEO_FORMATS`)
- **Duplicate Detection**: SHA256 checksum comparison
- **Balance Check**: Client must have sufficient minutes

**Validation Flow:**
1. Check file size and format
2. Calculate SHA256 checksum
3. Check for duplicate uploads in project
4. Verify user balance
5. Save and trigger pipeline

#### Signed URL Generation

All video streaming URLs are signed with expiration (1 hour default):

```python
from storage.b2_utils import get_b2_utils

b2_utils = get_b2_utils()
signed_url = b2_utils.generate_signed_url(b2_path, expiration=3600)
```

**Features:**
- Redis caching (1 hour TTL)
- Automatic retry on B2 errors
- Client never sees raw B2 credentials

### API Documentation

**Swagger UI**: `/api/docs/`
**OpenAPI Schema**: `/api/schema/`

The API is fully documented using DRF Spectacular with interactive Swagger UI.

## Usage Examples

### API Access (Python)

```python
import requests

# Obtain JWT token
response = requests.post('http://localhost:8000/api/auth/token/', json={
    'username': 'client@example.com',
    'password': 'password123'
})
token = response.json()['access']

# Use token in requests
headers = {'Authorization': f'Bearer {token}'}

# List projects
projects = requests.get('http://localhost:8000/api/projects/', headers=headers)

# Upload video
files = {'video_file': open('video.mp4', 'rb')}
data = {
    'project': 'project-uuid',
    'original_name': 'My Video'
}
response = requests.post(
    'http://localhost:8000/api/videos/',
    headers=headers,
    data=data,
    files=files
)

# Get signed streaming URL
video_id = response.json()['id']
signed = requests.get(
    f'http://localhost:8000/api/videos/{video_id}/signed-url/',
    headers=headers
)
stream_url = signed.json()['signed_url']
```

### HTMX Usage (HTML)

```html
<!-- Project list with auto-refresh -->
<div id="projects-list"
     hx-get="/client/htmx/projects/"
     hx-trigger="load, projectCreated from:body"
     hx-swap="innerHTML">
</div>

<!-- Create project button -->
<button hx-get="/client/htmx/projects/create/"
        hx-target="#modal-content"
        data-bs-toggle="modal"
        data-bs-target="#actionModal">
    Create Project
</button>

<!-- Upload video form -->
<form hx-post="/client/htmx/projects/{id}/upload/"
      hx-target="#videos-list"
      hx-encoding="multipart/form-data">
    {% csrf_token %}
    <input type="text" name="original_name" />
    <input type="file" name="video_file" accept="video/*" />
    <button type="submit">Upload</button>
</form>
```

## Testing

### Run Tests

```bash
# Run all tests
python manage.py test

# Run specific test suite
python manage.py test projects.tests_api_htmx
python manage.py test operators.tests_api

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Test Coverage

The implementation includes comprehensive tests for:
- JWT authentication flow
- API endpoint permissions
- Role-based access control
- File upload validation (size, format, duplicates)
- HTMX request/response flow
- Signed URL generation
- Verification task workflow
- Operator label creation

## Configuration

### Settings (`compliance_app/settings.py`)

```python
# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'PAGE_SIZE': 20,
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# Video validation
MAX_VIDEO_FILE_SIZE = 2147483648  # 2 GB
ALLOWED_VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'mkv', 'webm']
```

## Deployment Notes

1. **Environment Variables**:
   - Ensure `SECRET_KEY` is properly set
   - Configure `DATABASE_URL` for PostgreSQL
   - Set `REDIS_URL` for caching
   - Configure B2 credentials

2. **Static Files**:
   - Run `python manage.py collectstatic` for production
   - Serve via Whitenoise or CDN

3. **CORS** (if API accessed from different domain):
   - Install `django-cors-headers`
   - Configure allowed origins

4. **Rate Limiting** (recommended):
   - Consider adding DRF throttling for API endpoints
   - Implement rate limiting for file uploads

## Troubleshooting

### Common Issues

**JWT Token Invalid**
- Check token expiration
- Ensure correct `Authorization: Bearer <token>` header format
- Verify `SECRET_KEY` hasn't changed

**HTMX Not Loading**
- Check browser console for errors
- Verify HTMX script is loaded: `<script src="https://unpkg.com/htmx.org@1.9.10"></script>`
- Ensure `django_htmx` middleware is enabled

**Video Upload Fails**
- Check file size limits (nginx, Django)
- Verify allowed formats configuration
- Check user balance
- Review B2 credentials

**Signed URLs Expire Too Quickly**
- Adjust `expiration` parameter in `generate_signed_url()`
- Check Redis cache TTL settings

## Future Enhancements

- [ ] WebSocket support for real-time progress updates
- [ ] Batch video upload
- [ ] Video thumbnail generation
- [ ] Advanced filtering and search
- [ ] Export reports to PDF
- [ ] Webhook notifications for pipeline completion
- [ ] API versioning (v2)
