# Configuration Reference

This document provides a comprehensive reference for configuring the AI-Compliance Agent application. All configuration is managed through environment variables, with different settings for development and production environments.

## Table of Contents

- [Modular Settings Architecture](#modular-settings-architecture)
- [Environment Variables by Domain](#environment-variables-by-domain)
  - [Django Core](#django-core)
  - [Database](#database)
  - [Redis](#redis)
  - [Storage / Backblaze B2](#storage--backblaze-b2)
  - [Replicate AI Services](#replicate-ai-services)
  - [Email](#email)
  - [Cloudflare / CDN](#cloudflare--cdn)
  - [AI Pipeline](#ai-pipeline)
  - [Celery](#celery)
  - [Optional Tuning](#optional-tuning)
- [Configuration Examples](#configuration-examples)
- [Configuration Validator](#configuration-validator)
- [Secrets Management](#secrets-management)
- [Troubleshooting](#troubleshooting)

---

## Modular Settings Architecture

The application uses a modular settings structure to support different environments:

```
backend/compliance_app/settings/
├── __init__.py      # Automatic environment selection based on DJANGO_ENV
├── base.py          # Shared settings for all environments
├── dev.py           # Development settings (DEBUG=True, relaxed security)
└── prod.py          # Production settings (strict validation, security hardening)
```

### How Environment Selection Works

The `DJANGO_ENV` environment variable controls which settings module is loaded:

- **`development`** (or `dev`, `local`) → loads `dev.py`
- **`production`** (or `prod`, or unset) → loads `prod.py` (default)

**Important:** Always set `DJANGO_SETTINGS_MODULE=compliance_app.settings` (not `.dev` or `.prod`). The `__init__.py` file automatically imports the correct module based on `DJANGO_ENV`.

```bash
# Development
export DJANGO_ENV=development

# Production (default if not set)
export DJANGO_ENV=production
```

### Development Environment (`dev.py`)

Development settings are optimized for local testing and iteration:

- `DEBUG = True` (verbose error pages)
- `ALLOWED_HOSTS = ['*']` (no host restrictions)
- SQLite database by default (PostgreSQL optional via `DATABASE_URL`)
- Email printed to console (`console.EmailBackend`)
- No HTTPS redirects
- Replicate token optional (uses `dummy_token_for_dev` if not set)
- More verbose logging (`DEBUG` level)

### Production Environment (`prod.py`)

Production settings enforce security best practices and require complete configuration:

- `DEBUG = False` (mandatory)
- `ALLOWED_HOSTS` must be explicitly set (raises error if empty)
- PostgreSQL database required (raises error if not PostgreSQL)
- SMTP email required (all email vars mandatory)
- HTTPS redirects enabled by default
- Strict validation of all critical variables (raises errors on startup)
- Static file compression via WhiteNoise
- Redis-based caching
- Structured logging (INFO level by default)

---

## Environment Variables by Domain

### Django Core

Core Django configuration variables.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `DJANGO_ENV` | Environment selector (`development` or `production`) | No | `production` | Set to `development` for local work | Defaults to `production` for safety |
| `SECRET_KEY` | Django secret key for cryptographic signing | Yes | `unsafe-secret-key` | Can use default for local dev | **Must** be unique and secure; raises error if unsafe |
| `DEBUG` | Enable debug mode | No | `False` | Automatically `True` in dev.py | Must be `False` in production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames | No | `[]` | Set to `*` in dev.py | **Required** in production; raises error if empty |

**Security Notes:**
- Never use the default `SECRET_KEY` in production
- Generate a new key with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- In production, `SECRET_KEY` containing `unsafe-secret-key` or `django-insecure-` will cause startup failure

---

### Database

PostgreSQL database connection.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `DATABASE_URL` | Full database connection URL | Yes | `sqlite:///db.sqlite3` (dev only) | Can use SQLite for simple testing | **Must** be PostgreSQL; raises error otherwise |

**Format:**
```
postgres://username:password@host:port/database_name
```

**Examples:**
- Development: `postgres://postgres:postgres@localhost:5432/ai_compliance_dev`
- Docker Compose: `postgres://postgres:password@postgres:5432/compliance_db`
- Managed DB (DigitalOcean): `postgres://user:pass@db-postgresql-nyc3-12345.ondigitalocean.com:25060/defaultdb?sslmode=require`

---

### Redis

Redis connection for Celery and caching.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `REDIS_URL` | Full Redis connection URL | Yes | `redis://localhost:6379/0` | Local Redis instance | Managed Redis recommended (DigitalOcean, AWS ElastiCache, etc.) |

**Format:**
```
redis://[:password@]host:port/db_number
rediss://[:password@]host:port/db_number  # SSL variant
```

**Examples:**
- Development: `redis://localhost:6379/0`
- Docker Compose: `redis://redis:6379/0`
- Managed Redis with SSL: `rediss://default:password@redis-cluster.example.com:25061`

**Note:** Redis is used for:
- Celery broker (task queue)
- Celery result backend
- Django cache (production only)
- Signed URL caching (B2 storage)

---

### Storage / Backblaze B2

Backblaze B2 object storage configuration with retry settings.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `BACKBLAZE_ENDPOINT_URL` | S3-compatible endpoint URL | Yes | `''` | Get from B2 bucket settings | **Required**; raises error if empty |
| `BACKBLAZE_APPLICATION_KEY_ID` | B2 application key ID | Yes | `''` | From B2 account > App Keys | **Required**; raises error if empty |
| `BACKBLAZE_APPLICATION_KEY` | B2 application key (secret) | Yes | `''` | From B2 account > App Keys | **Required**; raises error if empty; keep secret |
| `BACKBLAZE_BUCKET_NAME` | B2 bucket name | Yes | `''` | Create bucket in B2 dashboard | **Required**; raises error if empty |
| `B2_MAX_RETRIES` | Maximum retry attempts for B2 operations | No | `3` | Use default | Increase for unreliable networks |
| `B2_RETRY_BACKOFF` | Exponential backoff multiplier | No | `2` | Use default | Higher = longer waits between retries |
| `B2_RETRY_BACKOFF_MAX` | Maximum backoff time (seconds) | No | `60` | Use default | Cap on exponential backoff |

**Setup Instructions:**

1. Sign up at [Backblaze B2](https://www.backblaze.com/b2/sign-up.html)
2. Create a bucket:
   - **Bucket Name:** `ai-compliance-videos` (or your choice)
   - **Files in Bucket:** Private
3. Create Application Key:
   - Navigate to **App Keys → Add a New Application Key**
   - **Key Name:** `ai-compliance-production`
   - **Allow access to:** All
   - **Type of Access:** Read and Write
4. Save credentials:
   - Copy `keyID` → `BACKBLAZE_APPLICATION_KEY_ID`
   - Copy `applicationKey` → `BACKBLAZE_APPLICATION_KEY`
5. Find Endpoint:
   - Go to **Buckets → [Your Bucket] → Endpoint**
   - Example: `https://s3.us-west-000.backblazeb2.com`

**Retry Logic:**
- All B2 operations use the `B2Utils` wrapper with tenacity-based retries
- Exponential backoff: waits 1s, 2s, 4s, ..., up to `B2_RETRY_BACKOFF_MAX`
- Retries on `ClientError` and `OSError`

**Artifact Retention:**
- Completed pipelines: artifacts deleted after 7 days
- Failed pipelines: artifacts retained for 14 days (for debugging)
- Temporary files (frames, audio): deleted after 24 hours
- Signed URL cache TTL: 1 hour (Redis)

---

### Replicate AI Services

Configuration for Replicate API and AI models.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `REPLICATE_API_TOKEN` | Replicate API authentication token | Yes | `''` | Set to `dummy_token_for_dev` if not provided | **Required**; raises error if empty |
| `REPLICATE_TIMEOUT` | API request timeout (seconds) | No | `300` | Use default | Increase for large videos |
| `WHISPER_MODEL_ID` | Replicate model ID for speech recognition | No | `openai/whisper:4d50797...` | Use default | Can override with custom model |
| `YOLO_MODEL_ID` | Replicate model ID for object detection | No | `adirik/yolov8:...` | Use default | Can override with custom model |
| `NSFW_MODEL_ID` | Replicate model ID for NSFW detection | No | `lucataco/nsfw-image-detection:...` | Use default | Can override with custom model |
| `VIOLENCE_MODEL_ID` | Replicate model ID for violence detection | No | `lucataco/vit-violence-detection:...` | Use default | Can override with custom model |
| `OCR_MODEL_ID` | Replicate model ID for text extraction | No | `abiruyt/text-extract-ocr:...` | Use default | Can override with custom model |

**Setup Instructions:**

1. Sign up at [Replicate](https://replicate.com)
2. Navigate to [API Tokens](https://replicate.com/account/api-tokens)
3. Create a new token or copy existing one
4. Token format: `r8_...`

**Model Defaults:**
- **OpenAI Whisper Small:** ASR (Automatic Speech Recognition)
- **YOLOv8:** Object detection
- **NSFW Detection:** Adult content detection
- **Violence Detection:** Gore and violence detection
- **EasyOCR:** Text extraction from frames

You can use any compatible Replicate models by overriding the `*_MODEL_ID` variables.

---

### Email

SMTP email configuration for notifications.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `EMAIL_BACKEND` | Django email backend class | No | `console` (dev) / `smtp` (prod) | Console output in dev | SMTP required in production |
| `EMAIL_HOST` | SMTP server hostname | Yes (prod) | `localhost` (dev) | Not used in dev (console backend) | **Required** in production |
| `EMAIL_PORT` | SMTP server port | No | `587` | Not used in dev | Typically 587 (TLS) or 465 (SSL) |
| `EMAIL_USE_TLS` | Use TLS encryption | No | `True` | Not used in dev | Recommended `True` for port 587 |
| `EMAIL_HOST_USER` | SMTP username | Yes (prod) | `''` | Not used in dev | **Required** in production |
| `EMAIL_HOST_PASSWORD` | SMTP password | Yes (prod) | `''` | Not used in dev | **Required** in production; use app-specific password |
| `DEFAULT_FROM_EMAIL` | Default sender email address | Yes (prod) | `noreply@localhost` (dev) | Not used in dev | **Required** in production |
| `ADMIN_EMAIL` | Admin notification email | No | `admin@localhost` | Use default | Set to receive error notifications |

**SMTP Provider Examples:**

**Gmail:**
1. Enable 2FA on your Google account
2. Create App Password: [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Configuration:
   ```env
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=app-password-here
   ```

**SendGrid:**
```env
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

**Mailgun:**
```env
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=postmaster@yourdomain.com
EMAIL_HOST_PASSWORD=your-mailgun-smtp-password
```

**Notifications Sent:**
- **Success:** When video report is ready for verification (template: `emails/video_ready.html`)
- **Failure:** When pipeline fails (includes error details, sent to project owner and admin)

---

### Cloudflare / CDN

Optional Cloudflare CDN integration for B2 storage.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `CLOUDFLARE_CDN_URL` | Cloudflare CDN URL for B2 | No | `''` | Not needed for dev | Recommended for production (faster delivery) |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token | No | `''` | Not needed | Required if using cache purge |
| `CLOUDFLARE_ZONE_ID` | Cloudflare Zone ID | No | `''` | Not needed | Required if using cache purge |

**Setup Instructions (Optional):**

1. Sign up at [Cloudflare](https://cloudflare.com)
2. Add your domain to Cloudflare
3. Configure DNS:
   - Create CNAME record: `cdn` → `f000.backblazeb2.com` (from B2 bucket settings)
   - Enable **Proxied** (orange cloud icon)
4. Create API Token:
   - Navigate to [API Tokens](https://dash.cloudflare.com/profile/api-tokens)
   - Permissions: **Zone - Cache Purge**, **Zone - Zone Read**
5. Find Zone ID in your domain's dashboard overview

**Benefits:**
- Faster global content delivery
- Automatic caching of videos and frames
- DDoS protection
- Bandwidth cost reduction

**Periodic Tasks:**
- `refresh_cdn_cache_periodic`: Refreshes CDN cache hourly (if configured)

---

### AI Pipeline

Video processing and AI pipeline configuration.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `MAX_VIDEO_FILE_SIZE` | Maximum video file size (bytes) | No | `2147483648` (2GB) | Use default or lower for testing | Adjust based on needs; 2GB recommended |
| `MAX_VIDEO_DURATION` | Maximum video duration (seconds) | No | `7200` (2 hours) | Use default or lower for testing | Adjust based on needs |
| `FRAME_EXTRACTION_FPS` | Frames per second to extract | No | `1` | Use default | Higher = more frames, longer processing |
| `ALLOWED_VIDEO_FORMATS` | Comma-separated allowed formats | No | `mp4,avi,mov,mkv,webm` | Use default | Add/remove formats as needed |
| `DASHBOARD_URL` | Dashboard URL for email links | No | `https://app.example.com` | Set to local URL | Set to production domain |
| `TEMP_DIR` | Temporary directory for processing | No | `/tmp` | Use default | Ensure sufficient disk space |
| `PROFANITY_DICT_PATH` | Path to profanity dictionary file | No | `''` | Optional | Optional; for custom profanity detection |
| `BRAND_DICT_PATH` | Path to brand names dictionary file | No | `''` | Optional | Optional; for brand mention detection |
| `STOPWORDS_DICT_PATH` | Path to stopwords dictionary file | No | `''` | Optional | Optional; for NLP processing |

**Video Validation:**

Before pipeline execution, videos are validated for:
- File size ≤ `MAX_VIDEO_FILE_SIZE`
- Duration ≤ `MAX_VIDEO_DURATION`
- Format in `ALLOWED_VIDEO_FORMATS`
- File existence and readability

If validation fails, the video is marked as `FAILED` and a notification is sent via `notify_validation_failure()`.

**SHA256 Checksum:**
- All uploaded videos have a SHA256 checksum calculated
- Used for duplicate detection

**Pipeline Resilience:**

Each Celery task in `ai_pipeline/celery_tasks.py` has:
- Automatic retry configuration (`autoretry_for`)
- Exponential backoff (`retry_backoff`)
- Time limits (`time_limit`, `soft_time_limit`)
- Progress tracking in `PipelineExecution` model (fields: `last_step`, `retry_count`, `error_trace`)

**Structured Logging:**

All pipeline steps log in JSON format via `log_pipeline_step()`:
```json
{
  "timestamp": "2024-01-01T12:00:00.000000",
  "video_id": "uuid-here",
  "step": "preprocess_video",
  "status": "completed",
  "error": null
}
```

---

### Celery

Celery distributed task queue configuration.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `REDIS_URL` | Celery broker and result backend | Yes | `redis://localhost:6379/0` | See [Redis](#redis) | See [Redis](#redis) |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | Max tasks per worker before restart | No | `100` | Use default | Lower if memory leaks occur |

**Task Queues:**
- `ai_pipeline`: AI processing tasks (video analysis, model inference)
- `projects`: Project management tasks
- `operators`: Operator notification tasks

**Celery Beat Schedule (Periodic Tasks):**
- `cleanup_artifacts_periodic`: Runs daily at 2:00 UTC (removes old B2 artifacts)
- `refresh_cdn_cache_periodic`: Runs hourly (updates CDN cache if Cloudflare configured)

**Worker Configuration:**
- Prefetch multiplier: `1` (one task at a time per worker)
- Late acks: `True` (acknowledge task only after completion)
- Task serialization: JSON

**Development Tip:**

For synchronous testing (no Celery/Redis needed), uncomment in `dev.py`:
```python
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

---

### Optional Tuning

Advanced configuration for performance and security tuning.

| Variable | Description | Required | Default | Dev Notes | Prod Notes |
|----------|-------------|----------|---------|-----------|------------|
| `LOG_LEVEL` | Logging level | No | `DEBUG` (dev) / `INFO` (prod) | Use `DEBUG` | Use `INFO` or `WARNING` |
| `SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS | No | `False` (dev) / `True` (prod) | Not used in dev | Enabled by default in prod |
| `SESSION_COOKIE_SECURE` | Require HTTPS for session cookies | No | `False` (dev) / `True` (prod) | Not used in dev | Enabled by default in prod |
| `CSRF_COOKIE_SECURE` | Require HTTPS for CSRF cookies | No | `False` (dev) / `True` (prod) | Not used in dev | Enabled by default in prod |
| `SECURE_HSTS_SECONDS` | HTTP Strict Transport Security duration | No | `0` (dev) / `31536000` (prod) | Not used in dev | 1 year by default |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | Apply HSTS to subdomains | No | `False` (dev) / `True` (prod) | Not used in dev | Enabled by default in prod |
| `SECURE_HSTS_PRELOAD` | Allow HSTS preload list inclusion | No | `False` (dev) / `True` (prod) | Not used in dev | Enabled by default in prod |

**Security Headers (Production):**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

**Session Settings (Production):**
- Cookie age: 2 weeks
- HTTPOnly: `True`
- SameSite: `Strict`

**CSRF Settings (Production):**
- HTTPOnly: `True`
- SameSite: `Strict`

---

## Configuration Examples

### Development Environment

**File:** `.env`

```env
# Django Core
DJANGO_ENV=development
SECRET_KEY=dev-secret-key-not-for-production
DEBUG=True

# Database (SQLite for simple dev, or PostgreSQL)
DATABASE_URL=sqlite:///db.sqlite3
# DATABASE_URL=postgres://postgres:postgres@localhost:5432/ai_compliance_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Backblaze B2 (minimal for dev testing)
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=test_key_id
BACKBLAZE_APPLICATION_KEY=test_key
BACKBLAZE_BUCKET_NAME=test-bucket

# Replicate (optional in dev, will use dummy token if not set)
REPLICATE_API_TOKEN=r8_your_token_here

# Email (console output in dev, no SMTP needed)
# EMAIL_BACKEND is automatically set to console in dev.py

# AI Pipeline (optional, defaults work)
MAX_VIDEO_FILE_SIZE=1073741824  # 1GB for dev testing
DASHBOARD_URL=http://localhost:8000
```

### Production Environment (Docker Compose)

**File:** `.env.docker` or `.env`

```env
# Django Core
DJANGO_ENV=production
SECRET_KEY=your-unique-secret-key-generate-with-django
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,app.yourdomain.com

# Database (Docker Compose managed)
DATABASE_URL=postgres://postgres:strongpassword@postgres:5432/compliance_db

# Redis (Docker Compose managed)
REDIS_URL=redis://redis:6379/0

# Backblaze B2
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=000a1b2c3d4e5f6789abc
BACKBLAZE_APPLICATION_KEY=K000AbCdEfGhIjKlMnOpQrStUvWxYz
BACKBLAZE_BUCKET_NAME=ai-compliance-production

# Cloudflare CDN (optional but recommended)
CLOUDFLARE_CDN_URL=https://cdn.yourdomain.com
CLOUDFLARE_API_TOKEN=your-cloudflare-api-token
CLOUDFLARE_ZONE_ID=your-cloudflare-zone-id

# Replicate
REPLICATE_API_TOKEN=r8_abc123def456ghi789jkl

# Email (SMTP)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com

# AI Pipeline
MAX_VIDEO_FILE_SIZE=2147483648  # 2GB
MAX_VIDEO_DURATION=7200  # 2 hours
FRAME_EXTRACTION_FPS=1
DASHBOARD_URL=https://app.yourdomain.com

# Performance Tuning
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
LOG_LEVEL=INFO
```

### Production Environment (DigitalOcean App Platform)

**File:** Environment variables in DigitalOcean dashboard

```env
# Django Core
DJANGO_ENV=production
SECRET_KEY=${SECRET_KEY}  # Set in DigitalOcean secrets
DEBUG=False
ALLOWED_HOSTS=yourapp.ondigitalocean.app,yourdomain.com,www.yourdomain.com

# Database (DigitalOcean Managed Database)
DATABASE_URL=${db.DATABASE_URL}  # Auto-injected by DigitalOcean

# Redis (DigitalOcean Managed Redis)
REDIS_URL=${redis.REDIS_URL}  # Auto-injected by DigitalOcean

# Backblaze B2
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=${BACKBLAZE_KEY_ID}  # Set in secrets
BACKBLAZE_APPLICATION_KEY=${BACKBLAZE_KEY}  # Set in secrets
BACKBLAZE_BUCKET_NAME=ai-compliance-production

# Cloudflare CDN
CLOUDFLARE_CDN_URL=https://cdn.yourdomain.com
CLOUDFLARE_API_TOKEN=${CLOUDFLARE_TOKEN}  # Set in secrets
CLOUDFLARE_ZONE_ID=${CLOUDFLARE_ZONE}  # Set in secrets

# Replicate
REPLICATE_API_TOKEN=${REPLICATE_TOKEN}  # Set in secrets

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=${SENDGRID_API_KEY}  # Set in secrets
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com

# AI Pipeline
MAX_VIDEO_FILE_SIZE=2147483648
MAX_VIDEO_DURATION=7200
FRAME_EXTRACTION_FPS=1
DASHBOARD_URL=https://yourapp.ondigitalocean.app

# Performance
TEMP_DIR=/tmp
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
LOG_LEVEL=INFO
```

---

## Configuration Validator

The application includes a configuration validator to check for missing or insecure settings before deployment.

### Running the Validator

```bash
# Manual validation
python backend/compliance_app/config_validator.py

# With specific environment
DJANGO_ENV=production python backend/compliance_app/config_validator.py
```

### Validator Output

**Success (all checks pass):**

```
====================================================================
📋 RESULTS OF CONFIGURATION VALIDATION
====================================================================

✅ Configuration is valid! All variables are set correctly.
```

**Success with warnings:**

```
====================================================================
📋 RESULTS OF CONFIGURATION VALIDATION
====================================================================

⚠️  WARNINGS:
  ⚠️  WARNING: CLOUDFLARE_CDN_URL not set (recommended for production)
  ⚠️  WARNING: ADMIN_EMAIL not set

✅ Configuration is valid (with warnings).
```

**Critical errors:**

```
====================================================================
📋 RESULTS OF CONFIGURATION VALIDATION
====================================================================

🚨 CRITICAL ERRORS:
  ❌ ERROR: Required variable REPLICATE_API_TOKEN not set
  ❌ SECURITY ERROR: SECRET_KEY contains unsafe value! Generate a new SECRET_KEY for production.
  ❌ ERROR: Required variable BACKBLAZE_ENDPOINT_URL not set

⚠️  WARNINGS:
  ⚠️  WARNING: DEBUG=True in production is unsafe!
  ⚠️  WARNING: REPLICATE_API_TOKEN should start with 'r8_'. Check token validity.

❌ Configuration is invalid! Fix errors before starting.

💡 Tip: Check your .env file or environment variables.
💡 Example: .env.example
```

### Automatic Validation on Startup

In production mode (`DEBUG=False`), the validator runs automatically on application startup via `prod.py`:

- If validation fails, the application **will not start**
- Errors are printed to console
- Process exits with code `1`

In development mode (`DEBUG=True`), validation is **skipped** to allow flexible local testing.

### What the Validator Checks

**Required Variables:**
- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `REPLICATE_API_TOKEN`
- `BACKBLAZE_ENDPOINT_URL`
- `BACKBLAZE_APPLICATION_KEY_ID`
- `BACKBLAZE_APPLICATION_KEY`
- `BACKBLAZE_BUCKET_NAME`

**Recommended Variables (warnings only):**
- `CLOUDFLARE_CDN_URL`
- `EMAIL_HOST`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

**Security Checks:**
- `SECRET_KEY` does not contain `unsafe-secret-key` or `django-insecure-`
- `DEBUG` is not `True` in production

**Format Checks:**
- `DATABASE_URL` starts with `postgres://` or `postgresql://`
- `REDIS_URL` starts with `redis://` or `rediss://`
- `REPLICATE_API_TOKEN` starts with `r8_` (warning if not)
- `BACKBLAZE_ENDPOINT_URL` starts with `https://s3.` (warning if not)

---

## Secrets Management

### Docker Compose

**Option 1: `.env` file (recommended for development)**

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://...
```

Docker Compose automatically loads `.env` and makes variables available to services.

**Option 2: `.env.docker` file**

Use a separate file for Docker-specific config:

```bash
docker compose --env-file .env.docker up -d
```

**Option 3: Docker secrets (recommended for production)**

For production Docker deployments, use Docker secrets:

```yaml
# docker-compose.prod.yml
services:
  web:
    secrets:
      - db_password
      - replicate_token
    environment:
      DATABASE_PASSWORD_FILE: /run/secrets/db_password
      REPLICATE_API_TOKEN_FILE: /run/secrets/replicate_token

secrets:
  db_password:
    file: ./secrets/db_password.txt
  replicate_token:
    file: ./secrets/replicate_token.txt
```

**Security Best Practices:**
- Add `.env` to `.gitignore` (never commit secrets)
- Use `.env.example` as a template without real values
- Restrict file permissions: `chmod 600 .env`
- Use separate `.env` files for dev/staging/prod environments

### DigitalOcean App Platform

DigitalOcean provides built-in secrets management:

**1. Environment Variables:**
- Go to your app → Settings → App-Level Environment Variables
- Add non-sensitive config (e.g., `DJANGO_ENV=production`)

**2. Secret Variables:**
- Use "Encrypt" option for sensitive data
- Encrypted variables are hidden in UI and logs
- Examples: `SECRET_KEY`, `REPLICATE_API_TOKEN`, `EMAIL_HOST_PASSWORD`

**3. Managed Resources:**
- Database and Redis URLs are auto-injected as `${db.DATABASE_URL}` and `${redis.REDIS_URL}`
- No need to manually configure connection strings

**4. Variable Scoping:**
- **App-level:** Shared across all components (web, worker, etc.)
- **Component-level:** Specific to one service

**Security Best Practices:**
- Mark all tokens/passwords as encrypted
- Use DigitalOcean's "Reference a Secret" feature
- Enable "Audit Logs" to track config changes
- Rotate secrets regularly (update in DigitalOcean → redeploy)

### AWS / Other Cloud Providers

**AWS Secrets Manager:**
```python
# Example: Load secrets at runtime
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In settings.py (if using AWS)
# secrets = get_secret('ai-compliance/production')
# SECRET_KEY = secrets['SECRET_KEY']
```

**Environment Variable Injection:**
Most platforms support injecting secrets as environment variables:
- AWS ECS: Task definition environment variables
- Google Cloud Run: Secrets Manager integration
- Azure App Service: Application settings

---

## Troubleshooting

### Common Configuration Errors

#### Error: "REPLICATE_API_TOKEN must be set"

**Cause:** Replicate token is missing or empty in production.

**Solution:**
```env
REPLICATE_API_TOKEN=r8_your_token_here
```

Get token from [Replicate API Tokens](https://replicate.com/account/api-tokens).

---

#### Error: "Backblaze credentials missing"

**Cause:** One or more B2 variables are not set.

**Solution:** Ensure all 4 variables are set:
```env
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=000abc123...
BACKBLAZE_APPLICATION_KEY=K000AbC...
BACKBLAZE_BUCKET_NAME=ai-compliance-videos
```

Check the [Backblaze B2 setup instructions](#storage--backblaze-b2) above.

---

#### Error: "Cannot connect to database"

**Cause:** `DATABASE_URL` is incorrect or database is not running.

**Solution:**

1. **Check URL format:**
   ```env
   # Correct:
   DATABASE_URL=postgres://user:password@host:5432/dbname
   
   # Also works:
   DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```

2. **Check database is running:**
   ```bash
   # For Docker Compose:
   docker compose ps postgres
   
   # For local PostgreSQL:
   pg_isready -h localhost -p 5432
   ```

3. **Check credentials:**
   ```bash
   psql "postgres://user:password@host:5432/dbname"
   ```

---

#### Error: "Cannot connect to Redis"

**Cause:** `REDIS_URL` is incorrect or Redis is not running.

**Solution:**

1. **Check URL format:**
   ```env
   # Correct (no auth):
   REDIS_URL=redis://localhost:6379/0
   
   # With password:
   REDIS_URL=redis://:password@localhost:6379/0
   
   # With SSL:
   REDIS_URL=rediss://default:password@host:25061
   ```

2. **Check Redis is running:**
   ```bash
   # For Docker Compose:
   docker compose ps redis
   
   # For local Redis:
   redis-cli -h localhost -p 6379 ping
   # Should return: PONG
   ```

---

#### Error: "ALLOWED_HOSTS must be set in production"

**Cause:** `ALLOWED_HOSTS` is empty in production (`prod.py` raises error).

**Solution:**
```env
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,app.yourdomain.com
```

**Note:** Comma-separated list, no spaces.

---

#### Error: "SECRET_KEY contains unsafe value"

**Cause:** Using default or insecure `SECRET_KEY` in production.

**Solution:** Generate a new key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy output to `.env`:
```env
SECRET_KEY=generated-key-here
```

---

#### Error: "PostgreSQL is required in production"

**Cause:** Using SQLite or non-PostgreSQL database in production.

**Solution:** Set `DATABASE_URL` to a PostgreSQL connection:
```env
DATABASE_URL=postgres://user:password@host:5432/dbname
```

SQLite is only allowed in development (`dev.py`).

---

#### Warning: "DEBUG=True in production is unsafe"

**Cause:** `DEBUG` is set to `True` in production.

**Solution:**
```env
DEBUG=False
```

Or remove `DEBUG` from `.env` entirely (defaults to `False` in `prod.py`).

---

#### Email not sending (production)

**Cause:** Missing or incorrect email configuration.

**Solution:** Ensure all email variables are set:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

**Test email:**
```bash
docker compose exec web python manage.py shell

from django.core.mail import send_mail
send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
```

---

#### Celery tasks not running

**Cause:** Celery worker not started or Redis connection issue.

**Solution:**

1. **Check Celery worker:**
   ```bash
   # Docker Compose:
   docker compose ps celery-worker
   docker compose logs celery-worker
   
   # Local:
   celery -A compliance_app worker --loglevel=info
   ```

2. **Check Redis connection:**
   ```bash
   redis-cli -h localhost -p 6379 ping
   ```

3. **Check Celery can connect:**
   ```bash
   docker compose exec web python manage.py shell
   
   from celery import current_app
   current_app.connection().connect()
   ```

---

## Additional Documentation

For more information, see:

- **[API Reference](./API.md)** - Complete REST API and HTMX documentation
- **[Architecture Overview](./ARCHITECTURE.md)** - System architecture and design decisions
- **[Deployment Guide](../DEPLOYMENT.md)** - Docker Compose and production deployment instructions
- **Development Guide** - Local development setup and workflows _(coming soon: `docs/DEVELOPMENT.md`)_

---

## Support

If you encounter issues not covered in this guide:

1. Check [Troubleshooting](#troubleshooting) section above
2. Run the [Configuration Validator](#configuration-validator)
3. Review logs: `docker compose logs web` or `docker compose logs celery-worker`
4. Verify environment with: `docker compose exec web python manage.py shell` → `import os; print(os.environ)`

For persistent issues, contact your system administrator or DevOps team.
