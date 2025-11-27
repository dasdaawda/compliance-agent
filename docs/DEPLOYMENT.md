# 🚀 Production Deployment Manual

## Table of Contents

1. [Prerequisites & Requirements](#prerequisites--requirements)
2. [Secrets & Security Setup](#secrets--security-setup)
3. [Environment Variables Configuration](#environment-variables-configuration)
4. [Multi-stage Dockerfile Usage](#multi-stage-dockerfile-usage)
5. [Production Docker Compose](#production-docker-compose)
6. [Database & Redis Provisioning](#database--redis-provisioning)
7. [Running Migrations & Collectstatic](#running-migrations--collectstatic)
8. [Rolling Deployments](#rolling-deployments)
9. [Health Checks & Monitoring](#health-checks--monitoring)
10. [Scaling Celery Workers](#scaling-celery-workers)
11. [Backup & Restore Procedures](#backup--restore-procedures)
12. [Troubleshooting Guide](#troubleshooting-guide)
13. [Post-Deployment Verification](#post-deployment-verification)

---

## Prerequisites & Requirements

### Required Accounts & Services

Before starting production deployment, ensure you have access to:

- ✅ **Cloud Provider Account** (DigitalOcean, AWS, GCP, Azure)
- ✅ **Backblaze B2 Account** for object storage
- ✅ **Replicate.com Account** for AI inference
- ✅ **Cloudflare Account** (recommended for CDN)
- ✅ **Email Service** (SendGrid, Mailgun, AWS SES, or Gmail with App Password)
- ✅ **Domain Name** (optional but recommended)

### Infrastructure Requirements

**Minimum Production Specifications:**
- **Web Server:** 2 GB RAM, 2 vCPU, 20 GB SSD
- **Database:** PostgreSQL 13+ with 4 GB RAM, 2 vCPU, 40 GB SSD
- **Redis:** 2 GB RAM, 1 vCPU
- **Celery Workers:** 2 GB RAM, 2 vCPU per worker
- **Storage:** Backblaze B2 (starting from 100 GB)

### Security Requirements

- SSL/TLS certificates (auto-provisioned by most platforms)
- Private database connections (SSL required)
- Private object storage buckets
- Environment variable encryption
- Regular security updates

---

## Secrets & Security Setup

### Generate Secure Secrets

```bash
# Generate Django SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate database password (32 characters)
openssl rand -base64 32

# Generate Redis password
openssl rand -hex 16
```

### Store Secrets Securely

**DigitalOcean App Platform:**
1. Go to Settings → App-Level Environment Variables
2. Use "Encrypt" checkbox for sensitive values
3. Reference with `${VARIABLE_NAME}` syntax

**Kubernetes:**
```bash
# Create secrets
kubectl create secret generic ai-compliance-secrets \
  --from-literal=secret-key='your-secret-key' \
  --from-literal=db-password='your-db-password' \
  --from-literal=redis-password='your-redis-password'
```

**Docker Swarm:**
```bash
# Create secrets
echo "your-secret-key" | docker secret create django_secret_key -
echo "your-db-password" | docker secret create db_password -
```

### Security Checklist

- [ ] All secrets stored in encrypted environment variables
- [ ] No hardcoded credentials in code or configuration files
- [ ] SSL/TLS enforced for all external connections
- [ ] Private object storage with signed URLs
- [ ] Database connections with `sslmode=require`
- [ ] Regular secret rotation schedule (quarterly)
- [ ] Access logging and monitoring enabled

---

## Environment Variables Configuration

### Core Application Variables

```env
# Django Core (Required)
DJANGO_ENV=production
SECRET_KEY=your-generated-secret-key
DEBUG=False
ALLOWED_HOSTS=.yourdomain.com,yourapp.ondigitalocean.app
DASHBOARD_URL=https://yourdomain.com

# Database (Required)
DATABASE_URL=postgres://user:password@host:port/database?sslmode=require

# Redis (Required)
REDIS_URL=rediss://:password@host:port

# Storage (Required)
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=your-key-id
BACKBLAZE_APPLICATION_KEY=your-application-key
BACKBLAZE_BUCKET_NAME=ai-compliance-videos

# AI Services (Required)
REPLICATE_API_TOKEN=r8_your_replicate_token

# Email (Required for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your_sendgrid_key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### Optional CDN Configuration

```env
# Cloudflare CDN (Recommended)
CLOUDFLARE_CDN_URL=https://cdn.yourdomain.com
CLOUDFLARE_API_TOKEN=your_cloudflare_token
CLOUDFLARE_ZONE_ID=your_zone_id
```

### Pipeline Configuration

```env
# Processing Limits
MAX_VIDEO_FILE_SIZE=2147483648  # 2GB in bytes
MAX_VIDEO_DURATION=7200          # 2 hours in seconds
FRAME_EXTRACTION_FPS=1           # Frames per second for analysis

# Retry Configuration
B2_MAX_RETRIES=5
B2_RETRY_BACKOFF=2
B2_RETRY_BACKOFF_MAX=60
REPLICATE_TIMEOUT=600            # 10 minutes
```

### Validation Command

Before deployment, validate your configuration:

```bash
# In Docker container
docker run --rm -v $(pwd):/app -w /app/backend python:3.11-slim \
  python manage.py check --deploy --settings compliance_app.settings

# In existing container
python manage.py check --deploy --settings compliance_app.settings
```

---

## Multi-stage Dockerfile Usage

### Build Process Overview

The multi-stage Dockerfile provides:

1. **Base Stage:** System dependencies and security setup
2. **Dependencies Stage:** Python packages with build tools
3. **Production Stage:** Minimal runtime image

### Building for Production

```bash
# Build production image
docker build -t ai-compliance:latest .

# Build with specific tag
docker build -t ai-compliance:v1.0.0 .

# Build without cache (for production releases)
docker build --no-cache -t ai-compliance:latest .
```

### Image Security Features

- **Non-root user:** Runs as `appuser` (UID 1000)
- **Minimal attack surface:** Only required system packages
- **Health checks:** Built-in container health monitoring
- **Read-only filesystem:** Recommended for production

### Running the Image

```bash
# Basic production run
docker run -d \
  --name ai-compliance-web \
  --env-file .env \
  -p 8000:8000 \
  ai-compliance:latest

# With read-only filesystem (recommended)
docker run -d \
  --name ai-compliance-web \
  --env-file .env \
  -p 8000:8000 \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /app/backend/tmp \
  ai-compliance:latest
```

---

## Production Docker Compose

### Production Compose Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  web:
    image: ai-compliance:latest
    restart: unless-stopped
    environment:
      - DJANGO_ENV=production
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    volumes:
      - static_volume:/app/backend/staticfiles
      - media_volume:/app/backend/media
      - tmp_volume:/tmp
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/login/').read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: '2'
        reservations:
          memory: 1G
          cpus: '1'

  celery-worker:
    image: ai-compliance:latest
    restart: unless-stopped
    command: celery -A compliance_app worker --loglevel=info --concurrency=2
    environment:
      - DJANGO_ENV=production
    env_file:
      - .env.production
    volumes:
      - tmp_volume:/tmp
    depends_on:
      - db
      - redis
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: '2'

  celery-beat:
    image: ai-compliance:latest
    restart: unless-stopped
    command: celery -A compliance_app beat --loglevel=info
    environment:
      - DJANGO_ENV=production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: ai_compliance
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  tmp_volume:
```

### Deployment Commands

```bash
# Deploy production stack
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Update with zero downtime
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-deps web
```

---

## Database & Redis Provisioning

### PostgreSQL Setup

**DigitalOcean Managed Database:**
1. Create PostgreSQL cluster (4GB RAM minimum)
2. Enable connection pooling
3. Configure trusted sources
4. Copy connection string

**AWS RDS:**
```bash
# Create parameter group for production
aws rds create-db-parameter-group \
  --db-parameter-group-name ai-compliance-prod \
  --db-parameter-group-family postgres15 \
  --description "Production params for AI Compliance"

# Set production parameters
aws rds modify-db-parameter-group \
  --db-parameter-group-name ai-compliance-prod \
  --parameters "ParameterName=max_connections,ParameterValue=200,ApplyMethod=immediate" \
  --parameters "ParameterName=shared_buffers,ParameterValue=1GB,ApplyMethod=pending-reboot"
```

**Database Connection Validation:**
```bash
# Test connection from application container
docker run --rm --network your-network \
  -e DATABASE_URL="$DATABASE_URL" \
  ai-compliance:latest \
  python manage.py dbshell
```

### Redis Setup

**DigitalOcean Managed Redis:**
1. Create Redis cluster (2GB RAM minimum)
2. Enable connection pooling
3. Configure eviction policy: `allkeys-lru`

**Redis Configuration:**
```conf
# redis.conf for production
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

**Connection Validation:**
```bash
# Test Redis connection
docker run --rm --network your-network \
  -e REDIS_URL="$REDIS_URL" \
  ai-compliance:latest \
  python -c "import redis; r=redis.from_url('$REDIS_URL'); print(r.ping())"
```

---

## Running Migrations & Collectstatic

### Entrypoint Script Automation

The `scripts/entrypoint.sh` automatically handles:

1. **Database readiness check** with retries
2. **Migration execution** with `--noinput`
3. **Static file collection** with `--clear`
4. **Application startup**

### Manual Migration Commands

```bash
# Run migrations manually
docker-compose exec web python manage.py migrate --noinput

# Create migrations for new models
docker-compose exec web python manage.py makemigrations

# Check migration status
docker-compose exec web python manage.py showmigrations

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput --clear
```

### Migration Best Practices

1. **Backup before major migrations:**
```bash
# Create database backup
pg_dump $DATABASE_URL > backup_before_migration.sql

# Test migrations on staging first
docker-compose -f docker-compose.staging.yml exec web python manage.py migrate --dry-run
```

2. **Zero-downtime migrations:**
```bash
# For large tables, use incremental migrations
docker-compose exec web python manage.py migrate --fake-initial

# Monitor migration progress
docker-compose exec web python manage.py migrate --verbosity=2
```

3. **Rollback procedures:**
```bash
# Rollback specific migration
docker-compose exec web python manage.py migrate app_name migration_name

# Restore from backup if needed
psql $DATABASE_URL < backup_before_migration.sql
```

---

## Rolling Deployments

### Blue-Green Deployment Strategy

```bash
# Deploy to green environment
docker-compose -f docker-compose.green.yml up -d

# Health check green environment
curl -f http://green.yourdomain.com/health/ || exit 1

# Switch traffic to green
# Update load balancer configuration

# Keep blue for rollback
docker-compose -f docker-compose.blue.yml stop
```

### Rolling Updates with Docker Compose

```bash
# Update web service with rolling restart
docker-compose -f docker-compose.prod.yml up -d --no-deps --scale web=2 web

# Update workers one by one
docker-compose -f docker-compose.prod.yml up -d --no-deps celery-worker

# Verify health after each service update
curl -f http://localhost:8000/health/
```

### Kubernetes Rolling Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-compliance-web
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: web
        image: ai-compliance:v1.0.0
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## Health Checks & Monitoring

### Application Health Endpoints

```python
# Add to urls.py
from django.http import JsonResponse

def health_check(request):
    """Comprehensive health check endpoint"""
    checks = {
        'database': check_database_connection(),
        'redis': check_redis_connection(),
        'storage': check_storage_connection(),
        'ai_service': check_replicate_connection(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JsonResponse({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks,
        'timestamp': timezone.now().isoformat()
    }, status=status_code)
```

### Docker Health Checks

```dockerfile
# In Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/login/').read()" || exit 1
```

### Monitoring Configuration

**Prometheus Metrics (optional):**
```python
# Add to settings.py
INSTALLED_APPS += ['django_prometheus']

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

**Log Aggregation:**
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

---

## Scaling Celery Workers

### Horizontal Scaling

```bash
# Scale workers based on queue length
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=5

# Monitor queue length
docker-compose exec celery-worker celery -A compliance_app inspect active
docker-compose exec celery-worker celery -A compliance_app inspect stats
```

### Worker Configuration

```python
# celery_config.py
from kombu import Queue

# Configure queues for different task types
task_routes = {
    'ai_pipeline.tasks.process_video': {'queue': 'video_processing'},
    'ai_pipeline.tasks.generate_report': {'queue': 'reports'},
    'ai_pipeline.tasks.cleanup_artifacts': {'queue': 'maintenance'},
}

# Worker concurrency settings
worker_concurrency = 2  # CPU cores * 2 for I/O bound tasks
worker_prefetch_multiplier = 1
task_acks_late = True
```

### Auto-scaling with Kubernetes

```yaml
# celery-worker-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Backup & Restore Procedures

### Database Backups

**Automated Daily Backups:**
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ai_compliance_$TIMESTAMP.sql"

# Create backup
pg_dump $DATABASE_URL > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_FILE.gz s3://your-backup-bucket/

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**Restore from Backup:**
```bash
# Stop application
docker-compose stop web celery-worker celery-beat

# Restore database
gunzip -c backup_file.sql.gz | psql $DATABASE_URL

# Restart application
docker-compose start web celery-worker celery-beat
```

### Object Storage Backups

**B2 Bucket Backup:**
```bash
# Sync to backup bucket
b2 sync --excludeAllSymlinks \
  --includeRegex ".*\.(mp4|avi|mov|mkv)$" \
  b2://ai-compliance-videos/ \
  b2://ai-compliance-backups/

# Cross-region replication (optional)
b2 sync --delete b2://ai-compliance-videos/ b2://ai-compliance-backup-eu/
```

### Configuration Backups

```bash
# Backup environment variables
printenv > .env.backup.$(date +%Y%m%d)

# Backup Docker configs
docker-compose -f docker-compose.prod.yml config > docker-compose.backup.yml
```

---

## Troubleshooting Guide

### Common Deployment Issues

#### 1. Database Connection Errors

**Symptoms:**
- `OperationalError: could not connect to server`
- Health checks failing
- Application startup timeouts

**Solutions:**
```bash
# Check database connectivity
docker-compose exec web python manage.py dbshell

# Verify connection string
echo $DATABASE_URL

# Test network connectivity
docker-compose exec web ping db-hostname

# Check SSL configuration
psql "postgres://user:pass@host:5432/db?sslmode=require"
```

#### 2. Celery Worker Issues

**Symptoms:**
- Tasks not processing
- Queue growing indefinitely
- Workers not starting

**Solutions:**
```bash
# Check worker status
docker-compose exec celery-worker celery -A compliance_app inspect active

# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Restart workers
docker-compose restart celery-worker

# Clear stuck tasks
docker-compose exec celery-worker celery -A compliance_app purge
```

#### 3. Storage Upload Failures

**Symptoms:**
- Video upload failures
- B2 authentication errors
- CORS issues

**Solutions:**
```bash
# Test B2 credentials
python -c "
import boto3
client = boto3.client('s3', **B2_CONFIG)
print(client.list_buckets())
"

# Check bucket permissions
b2 get-bucket ai-compliance-videos

# Verify CORS configuration
b2 get-bucket-cors-rules ai-compliance-videos
```

#### 4. Memory Issues

**Symptoms:**
- OOMKilled containers
- Slow performance
- High memory usage

**Solutions:**
```bash
# Check memory usage
docker stats

# Adjust worker concurrency
# Set CELERY_WORKER_CONCURRENCY=1 in environment

# Monitor with htop
docker-compose exec web htop
```

### Debug Mode Enablement

```bash
# Temporary debug mode
docker-compose exec web python manage.py shell

# Enable debug logging
export DJANGO_LOG_LEVEL=DEBUG

# Run with verbose output
docker-compose up --build
```

### Log Analysis

```bash
# View application logs
docker-compose logs -f web

# Filter error logs
docker-compose logs web | grep ERROR

# Monitor Celery worker logs
docker-compose logs -f celery-worker

# Export logs for analysis
docker-compose logs --no-color > app_logs.txt
```

---

## Post-Deployment Verification

### Django Deployment Check

```bash
# Run comprehensive deployment check
python manage.py check --deploy --settings compliance_app.settings
```

**Expected Output:**
```
System check identified no issues (0 silenced).
```

### Service Health Verification

```bash
# Check web service health
curl -f http://yourdomain.com/admin/login/

# Check API health
curl -f http://yourdomain.com/api/health/

# Verify static files
curl -I http://yourdomain.com/static/admin/css/base.css
```

### Database Operations Test

```bash
# Test database operations
python manage.py shell
>>> from projects.models import Project
>>> Project.objects.count()
>>> exit()
```

### Celery Tasks Verification

```bash
# Test Celery connectivity
docker-compose exec celery-worker celery -A compliance_app inspect ping

# Check scheduled tasks
docker-compose exec celery-beat celery -A compliance_app inspect scheduled

# Test task execution
python manage.py shell
>>> from ai_pipeline.celery_tasks import test_task
>>> test_task.delay()
```

### Email Configuration Test

```bash
# Test email sending
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test Subject', 'Test Body', 'from@example.com', ['to@example.com'])
```

### External Services Test

```bash
# Test B2 connectivity
python manage.py shell
>>> from storage.b2_utils import B2Utils
>>> B2Utils.test_connection()

# Test Replicate API
python manage.py shell
>>> from ai_pipeline.replicate_service import ReplicateService
>>> ReplicateService.test_connection()
```

### Performance Baseline

```bash
# Load testing with curl
for i in {1..100}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://yourdomain.com/
done

# Database query analysis
python manage.py shell
>>> from django.db import connection
>>> connection.queries
```

### Final Checklist

- [ ] All health checks passing
- [ ] Database migrations applied
- [ ] Static files collected and accessible
- [ ] Celery workers processing tasks
- [ ] Email notifications working
- [ ] File uploads to B2 successful
- [ ] AI pipeline processing videos
- [ ] SSL/TLS certificates valid
- [ ] Monitoring and logging configured
- [ ] Backup procedures tested
- [ ] Performance benchmarks recorded

---

## Related Documentation

- **[Configuration Guide](../CONFIGURATION.md)** - Detailed environment variable reference
- **[API Documentation](API.md)** - REST API and HTMX interface documentation
- **[Architecture Overview](ARCHITECTURE.md)** - System architecture and component details
- **[Development Setup](../README.md)** - Local development and testing procedures

---

## Support & Emergency Contacts

For deployment emergencies:

1. **Check logs first:** `docker-compose logs -f`
2. **Run health checks:** `python manage.py check --deploy`
3. **Verify all external services** (database, Redis, B2, Replicate)
4. **Document the issue** with timestamps and error messages

---

**Deployment Complete! 🎉**

Your AI Compliance Agent is now running in production with proper monitoring, scaling, and backup procedures.