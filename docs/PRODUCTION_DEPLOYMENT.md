# Production Deployment Guide / Руководство по развертыванию в Production

**Contents / Оглавление:**
- [English Version](#english-version)
- [Русская версия](#русская-версия)

---

## English Version

# Production Deployment Guide for AI-Compliance Agent

This comprehensive guide walks through deploying AI-Compliance Agent to production. It covers two deployment paths:
1. **Docker/Docker Compose** (recommended for managed platforms)
2. **Bare-metal with Gunicorn + systemd + Nginx** (for traditional VPS/dedicated servers)

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Host Preparation](#host-preparation)
3. [Secrets & Configuration Management](#secrets--configuration-management)
4. [Environment Setup](#environment-setup)
5. [Deployment Path 1: Docker Compose](#deployment-path-1-docker-compose)
6. [Deployment Path 2: Bare-Metal Gunicorn + systemd + Nginx](#deployment-path-2-bare-metal-gunicorn--systemd--nginx)
7. [Database Migrations & Static Collection](#database-migrations--static-collection)
8. [Celery Worker & Beat Services](#celery-worker--beat-services)
9. [Monitoring & Health Checks](#monitoring--health-checks)
10. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying to production, ensure you have:

- [ ] Generated a strong `SECRET_KEY` using: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Provisioned PostgreSQL database (v12+) with SSL support
- [ ] Provisioned Redis instance (v6+) with authentication
- [ ] Backblaze B2 account with:
  - [ ] Application Key ID and Key created
  - [ ] S3-compatible endpoint identified
  - [ ] Dedicated bucket for video storage created
- [ ] Cloudflare account (optional but recommended) with:
  - [ ] Zone DNS configured
  - [ ] B2 bucket CNAME configured to Cloudflare
  - [ ] API token created
- [ ] SSL/TLS certificate (Let's Encrypt or commercial)
- [ ] SMTP email account configured (Gmail, SendGrid, etc.)
- [ ] Domain name configured and pointing to server
- [ ] Server logs aggregation setup (optional: Sentry, LogRocket, etc.)

---

## Host Preparation

### For Ubuntu/Debian-based Systems

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  build-essential \
  curl \
  wget \
  git \
  ffmpeg \
  libmagic1 \
  libpq5 \
  ca-certificates \
  supervisor \
  nginx \
  certbot \
  python3-certbot-nginx

# Install Docker (if using Docker Compose deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Create Application User

```bash
# Create non-root user for running the application
sudo useradd -m -s /bin/bash -d /home/appuser appuser

# Add to sudo group (optional, for management)
sudo usermod -aG sudo appuser
```

### Create Application Directories

```bash
# As root or with sudo
sudo mkdir -p /opt/ai-compliance-agent
sudo mkdir -p /var/log/ai-compliance-agent
sudo mkdir -p /var/run/ai-compliance-agent
sudo chown -R appuser:appuser /opt/ai-compliance-agent /var/log/ai-compliance-agent /var/run/ai-compliance-agent
sudo chmod 755 /opt/ai-compliance-agent
```

---

## Secrets & Configuration Management

### Option 1: Environment File (.env) - Simple Approach

**Create and protect the .env file:**

```bash
# Navigate to application directory
cd /opt/ai-compliance-agent

# Copy example configuration
cp .env.example .env

# Edit with sensitive values
nano .env

# Set restrictive permissions (read-only for app user)
chmod 640 .env
sudo chown appuser:appuser .env
```

### Option 2: Secrets Manager - Enterprise Approach

For larger deployments, use a dedicated secrets manager:

**Using HashiCorp Vault:**
```bash
# Install Vault client
sudo apt-get install -y vault

# Configure Vault connection in application settings
# Set environment variables:
export VAULT_ADDR=https://vault.yourdomain.com
export VAULT_TOKEN=s.xxxxxxxxxxxxxxxx
```

**Using AWS Secrets Manager:**
```bash
# Install AWS CLI
pip install awscli

# Store secrets
aws secretsmanager create-secret --name ai-compliance/production --secret-string file://secrets.json

# Application code will fetch at startup via boto3
```

### Option 3: Dotenv Injection via CI/CD

**GitHub Actions / GitLab CI:**
```yaml
# Deploy job
deploy:
  script:
    - |
      cat > /opt/ai-compliance-agent/.env << EOF
      SECRET_KEY=$SECRET_KEY
      DATABASE_URL=$DATABASE_URL
      REDIS_URL=$REDIS_URL
      BACKBLAZE_APPLICATION_KEY_ID=$BACKBLAZE_APP_ID
      BACKBLAZE_APPLICATION_KEY=$BACKBLAZE_APP_KEY
      EOF
    - chmod 640 /opt/ai-compliance-agent/.env
    - docker compose -f /opt/ai-compliance-agent/docker-compose.yml up -d
```

### Recommended: Use .env + Secure Vault for Rotation

Combine approaches for best practices:
1. Store `.env` on server with restrictive permissions (640)
2. Use CI/CD to inject secrets into `.env` during deployment
3. Implement secret rotation via cron job + CI/CD hook

---

## Environment Setup

### Set DJANGO_ENV Variable

The application uses modular settings based on `DJANGO_ENV`:

```bash
# In .env file or shell environment
export DJANGO_ENV=production

# Or add to systemd service file (see below)
# Or add to docker-compose environment
```

This automatically loads `/backend/compliance_app/settings/prod.py` with:
- `DEBUG=False` (enforced)
- PostgreSQL requirement
- SMTP email requirement
- HTTPS security redirects
- Strict CSRF and cookie settings

### Validate Configuration

Before deployment, run the config validator:

```bash
cd /opt/ai-compliance-agent

# Load environment
export $(cat .env | xargs)

# Run validator
python backend/compliance_app/config_validator.py
```

Expected output:
```
============================================================
📋 RESULTS OF CONFIGURATION VALIDATION
============================================================

✅ Configuration is valid! All variables are set correctly.
```

### Required Environment Variables

Refer to `.env.example` for complete list. Key production variables:

**Django Core:**
```
DJANGO_ENV=production
SECRET_KEY=<unique-secure-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,cdn.yourdomain.com
```

**Database:**
```
DATABASE_URL=postgres://user:password@hostname:5432/dbname?sslmode=require
```

**Redis (with authentication):**
```
REDIS_URL=rediss://default:password@hostname:6379/0
```

**Backblaze B2:**
```
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=<key-id>
BACKBLAZE_APPLICATION_KEY=<secret-key>
BACKBLAZE_BUCKET_NAME=ai-compliance-videos
```

**Cloudflare CDN (optional):**
```
CLOUDFLARE_CDN_URL=https://cdn.yourdomain.com
CLOUDFLARE_ZONE_ID=<zone-id>
CLOUDFLARE_API_TOKEN=<api-token>
```

**Email Notifications:**
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-specific-password>
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
```

**Security Flags:**
```
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

---

## Deployment Path 1: Docker Compose

### Recommended For:
- DigitalOcean App Platform
- AWS ECS with Docker Compose
- GCP Cloud Run
- Any managed Docker hosting
- Simple production setups

### Prerequisites

```bash
# Ensure Docker and Docker Compose are installed
docker --version  # Should be 20.10+
docker compose version  # Should be 2.0+
```

### Setup

**1. Clone repository and configure:**

```bash
cd /opt/ai-compliance-agent
git clone <your-repo> .
cp .env.example .env

# Edit .env with production values
nano .env
```

**2. Create named volumes for persistence:**

```bash
docker volume create compliance-postgres-data
docker volume create compliance-redis-data
```

**3. Harden docker-compose.yml:**

Edit `docker-compose.yml` to ensure:
- Volume persistence: ✅ (already configured)
- Health checks: ✅ (already configured)
- Resource limits: Add these to web service:

```yaml
services:
  web:
    # ... existing config
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    restart_policy:
      condition: on-failure
      delay: 5s
      max_attempts: 5
  
  celery-worker:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

**4. Start services:**

```bash
# Pull latest images
docker compose pull

# Start all services (database, redis, web, celery, celery-beat)
docker compose up -d

# Check health
docker compose ps
docker compose logs web

# Wait for readiness (check for "Starting application" message)
docker compose logs --follow web | grep "Starting application"
```

**5. Run migrations:**

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
```

**6. Verify health endpoints:**

```bash
# Check main application
curl -H "Host: yourdomain.com" http://localhost:8000/admin/login/

# Check health endpoint (if exposed)
curl http://localhost:8000/health/
```

### Logging Configuration

By default, Docker Compose logs to stdout/stderr. For persistent logging:

**Option A: Docker logging drivers**

Add to `docker-compose.yml`:
```yaml
services:
  web:
    logging:
      driver: json-file
      options:
        max-size: "100m"
        max-file: "10"
        labels: "service=web"
```

**Option B: Centralized logging (e.g., ELK, Loki)**

```yaml
services:
  web:
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-batch-size: "400"
```

### Backup & Maintenance

**Daily backup script:**

```bash
#!/bin/bash
# /opt/ai-compliance-agent/scripts/backup.sh

BACKUP_DIR=/backups/ai-compliance-agent
DATE=$(date +%Y-%m-%d_%H-%M-%S)

# Backup PostgreSQL
docker compose exec -T postgres pg_dump -U postgres ai_compliance_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup Redis (optional)
docker compose exec -T redis redis-cli BGSAVE
docker compose cp redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "redis_*.rdb" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
0 2 * * * /opt/ai-compliance-agent/scripts/backup.sh >> /var/log/ai-compliance-agent/backup.log 2>&1
```

---

## Deployment Path 2: Bare-Metal Gunicorn + systemd + Nginx

### Recommended For:
- Traditional VPS (DigitalOcean Droplet, Linode, AWS EC2)
- On-premises servers
- Situations requiring full control
- Microservice deployments

### Prerequisites

```bash
# Ensure system packages installed (from Host Preparation section)
python3.11 --version
nginx --version
systemctl --version
```

### Setup

**1. Clone repository:**

```bash
cd /opt/ai-compliance-agent
git clone <your-repo> .
sudo chown -R appuser:appuser /opt/ai-compliance-agent
```

**2. Create Python virtual environment:**

```bash
cd /opt/ai-compliance-agent
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn[gevent]  # Production WSGI server

# Create .env file
cp .env.example .env
nano .env  # Edit with production values
```

**3. Run migrations and collect static files:**

```bash
cd /opt/ai-compliance-agent

# Load environment
export $(cat .env | xargs -0)

# Run migrations
python backend/manage.py migrate

# Create superuser
python backend/manage.py createsuperuser

# Collect static files
python backend/manage.py collectstatic --noinput --clear
```

**4. Create systemd service files:**

**a) Gunicorn service (django app):**

Create `/etc/systemd/system/ai-compliance-gunicorn.service`:

```ini
[Unit]
Description=AI-Compliance Agent - Gunicorn WSGI Server
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=appuser
WorkingDirectory=/opt/ai-compliance-agent
EnvironmentFile=/opt/ai-compliance-agent/.env

ExecStart=/opt/ai-compliance-agent/venv/bin/gunicorn \
    --workers=4 \
    --worker-class=gevent \
    --worker-connections=1000 \
    --timeout=120 \
    --access-logfile=/var/log/ai-compliance-agent/gunicorn-access.log \
    --error-logfile=/var/log/ai-compliance-agent/gunicorn-error.log \
    --bind=unix:/var/run/ai-compliance-agent/gunicorn.sock \
    backend.compliance_app.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**b) Celery Worker service:**

Create `/etc/systemd/system/ai-compliance-celery-worker.service`:

```ini
[Unit]
Description=AI-Compliance Agent - Celery Worker
After=network.target redis-server.service postgresql.service
Requires=ai-compliance-gunicorn.service

[Service]
Type=forking
User=appuser
WorkingDirectory=/opt/ai-compliance-agent
EnvironmentFile=/opt/ai-compliance-agent/.env

ExecStart=/opt/ai-compliance-agent/venv/bin/celery -A backend.compliance_app worker \
    --loglevel=info \
    --logfile=/var/log/ai-compliance-agent/celery-worker.log \
    --pidfile=/var/run/ai-compliance-agent/celery-worker.pid \
    --concurrency=4

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**c) Celery Beat service (periodic tasks):**

Create `/etc/systemd/system/ai-compliance-celery-beat.service`:

```ini
[Unit]
Description=AI-Compliance Agent - Celery Beat Scheduler
After=network.target redis-server.service postgresql.service
Requires=ai-compliance-gunicorn.service

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/ai-compliance-agent
EnvironmentFile=/opt/ai-compliance-agent/.env

ExecStart=/opt/ai-compliance-agent/venv/bin/celery -A backend.compliance_app beat \
    --loglevel=info \
    --logfile=/var/log/ai-compliance-agent/celery-beat.log \
    --pidfile=/var/run/ai-compliance-agent/celery-beat.pid \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**5. Enable and start services:**

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable ai-compliance-gunicorn.service
sudo systemctl enable ai-compliance-celery-worker.service
sudo systemctl enable ai-compliance-celery-beat.service

# Start services
sudo systemctl start ai-compliance-gunicorn.service
sudo systemctl start ai-compliance-celery-worker.service
sudo systemctl start ai-compliance-celery-beat.service

# Check status
sudo systemctl status ai-compliance-gunicorn.service
sudo systemctl status ai-compliance-celery-worker.service
sudo systemctl status ai-compliance-celery-beat.service

# View logs
sudo journalctl -u ai-compliance-gunicorn.service -f
sudo journalctl -u ai-compliance-celery-worker.service -f
sudo journalctl -u ai-compliance-celery-beat.service -f
```

**6. Configure Nginx (reverse proxy + TLS):**

Create `/etc/nginx/sites-available/ai-compliance-agent`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Certificate (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL Configuration (Modern)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Logging
    access_log /var/log/ai-compliance-agent/nginx-access.log;
    error_log /var/log/ai-compliance-agent/nginx-error.log;

    # Client upload size (match MAX_VIDEO_FILE_SIZE)
    client_max_body_size 2G;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_vary on;
    gzip_min_length 1000;

    # Static files (served directly by Nginx)
    location /static/ {
        alias /opt/ai-compliance-agent/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (served directly by Nginx, or proxy to B2)
    location /media/ {
        alias /opt/ai-compliance-agent/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://unix:/var/run/ai-compliance-agent/gunicorn.sock;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # WebSocket support (if needed for future real-time features)
    location /ws/ {
        proxy_pass http://unix:/var/run/ai-compliance-agent/gunicorn.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint
    location /health/ {
        proxy_pass http://unix:/var/run/ai-compliance-agent/gunicorn.sock;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        access_log off;
    }
}

# CDN upstream config (if using Cloudflare separately)
upstream b2_cdn {
    server cdn.yourdomain.com;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name cdn.yourdomain.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Forward requests to B2 via Cloudflare
    location / {
        proxy_pass https://b2_cdn;
        proxy_ssl_verify off;  # Cloudflare handles verification
        proxy_http_version 1.1;
        proxy_set_header Host $proxy_host;
        proxy_set_header Connection "";
    }
}
```

Enable Nginx site:
```bash
sudo ln -s /etc/nginx/sites-available/ai-compliance-agent /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Start/reload Nginx
sudo systemctl start nginx
sudo systemctl reload nginx
```

**7. Setup Let's Encrypt SSL certificate:**

```bash
# Install certificate
sudo certbot certonly --webroot -w /var/www/certbot \
    -d yourdomain.com -d www.yourdomain.com \
    --agree-tos --email admin@yourdomain.com

# Setup auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal (dry-run)
sudo certbot renew --dry-run

# Check renewal log
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Systemd Service Management

Common operations:

```bash
# Start/stop/restart services
sudo systemctl start ai-compliance-gunicorn.service
sudo systemctl stop ai-compliance-gunicorn.service
sudo systemctl restart ai-compliance-gunicorn.service

# View logs
sudo journalctl -u ai-compliance-gunicorn.service -n 100 -f

# Check service status
sudo systemctl status ai-compliance-gunicorn.service

# Enable/disable auto-start
sudo systemctl enable ai-compliance-gunicorn.service
sudo systemctl disable ai-compliance-gunicorn.service

# Full service stack status
sudo systemctl status ai-compliance-*.service
```

---

## Database Migrations & Static Collection

### Running Migrations

**Docker Compose:**
```bash
docker compose exec web python manage.py migrate --noinput
```

**Bare-metal:**
```bash
cd /opt/ai-compliance-agent
source venv/bin/activate
export $(cat .env | xargs)

python backend/manage.py migrate --noinput
```

### Static File Collection

This is handled automatically by `scripts/entrypoint.sh` in Docker, and by systemd service in bare-metal.

To manually collect static files:

```bash
# Docker Compose
docker compose exec web python manage.py collectstatic --noinput --clear

# Bare-metal
cd /opt/ai-compliance-agent/backend
python manage.py collectstatic --noinput --clear
```

### Django Check for Production

Always verify production configuration before going live:

```bash
# Docker Compose
docker compose exec web python manage.py check --deploy

# Bare-metal
cd /opt/ai-compliance-agent
source venv/bin/activate
export $(cat .env | xargs)

python backend/manage.py check --deploy
```

Expected output (with warnings for optional settings):
```
System check identified no critical issues.
```

---

## Celery Worker & Beat Services

### Architecture

- **Celery Worker**: Processes async tasks (video processing, AI inference, report compilation)
- **Celery Beat**: Runs periodic tasks (cleanup, CDN cache refresh)
- **Redis**: Message broker and result backend

### Configuration

Key settings in `.env`:

```bash
# Celery concurrency (number of parallel tasks)
CELERY_WORKER_CONCURRENCY=4

# Max tasks per worker before restart
CELERY_WORKER_MAX_TASKS_PER_CHILD=100

# Task timeouts
CELERY_TASK_TIME_LIMIT=3600       # 1 hour hard limit
CELERY_TASK_SOFT_TIME_LIMIT=3300  # 55 min soft warning
```

### Starting Services

**Docker Compose (automated):**
```bash
docker compose up -d celery-worker celery-beat
docker compose logs -f celery-worker celery-beat
```

**Bare-metal (systemd):**
```bash
sudo systemctl start ai-compliance-celery-worker.service
sudo systemctl start ai-compliance-celery-beat.service

# Monitor
sudo journalctl -u ai-compliance-celery-worker.service -f
```

### Monitoring Tasks

**Check running tasks:**
```bash
# Docker Compose
docker compose exec redis redis-cli

# Commands:
# KEYS celery:*        # List all Celery keys
# LLEN celery:queue:*  # Queue lengths
```

**Using Flower (Celery monitoring UI):**

```bash
# Install (development only)
pip install flower

# Run on port 5555
celery -A backend.compliance_app flower --port=5555

# Access at http://localhost:5555/
```

### Scheduled Tasks

Periodic tasks are configured via Django Celery Beat with database scheduler.

Key tasks:
- **cleanup_artifacts_periodic**: Removes old video artifacts (7 days)
- **refresh_cdn_cache_periodic**: Invalidates Cloudflare cache

View scheduled tasks:
```bash
# Django shell
python manage.py shell
from django_celery_beat.models import PeriodicTask
PeriodicTask.objects.all()
```

---

## Monitoring & Health Checks

### Application Health Check Endpoint

The application provides a health check endpoint (if implemented):

```bash
# Query health
curl https://yourdomain.com/health/

# Response (JSON)
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "workers: 1, tasks: 0"
}
```

If health endpoint doesn't exist, create one:

```python
# backend/compliance_app/urls.py
from django.http import JsonResponse

def health_check(request):
    from django.db import connection
    from redis import Redis
    import json
    
    status = {"status": "healthy"}
    
    try:
        # Database check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["database"] = "connected"
    except:
        status["status"] = "unhealthy"
        status["database"] = "disconnected"
    
    try:
        # Redis check
        r = Redis.from_url(os.getenv('REDIS_URL'))
        r.ping()
        status["redis"] = "connected"
    except:
        status["status"] = "unhealthy"
        status["redis"] = "disconnected"
    
    status_code = 200 if status["status"] == "healthy" else 503
    return JsonResponse(status, status=status_code)

# Add to urlpatterns:
path('health/', health_check, name='health'),
```

### Nginx Health Monitoring

Configure health check probes for load balancers:

```nginx
location /health/ {
    access_log off;
    proxy_pass http://gunicorn_backend;
    proxy_http_version 1.1;
}
```

### Service Status Monitoring

**Systemd service monitoring:**

```bash
# Check all services
sudo systemctl status ai-compliance-*.service

# Create monitoring script
cat > /opt/ai-compliance-agent/scripts/check_services.sh << 'EOF'
#!/bin/bash
SERVICES=(
    "ai-compliance-gunicorn"
    "ai-compliance-celery-worker"
    "ai-compliance-celery-beat"
)

for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service is running"
    else
        echo "❌ $service is NOT running"
        echo "  Attempting restart..."
        sudo systemctl restart $service
    fi
done
EOF

chmod +x /opt/ai-compliance-agent/scripts/check_services.sh

# Schedule in crontab (every 5 minutes)
*/5 * * * * /opt/ai-compliance-agent/scripts/check_services.sh >> /var/log/ai-compliance-agent/service-checks.log 2>&1
```

### Log Aggregation

**Docker Compose logging:**

```yaml
# In docker-compose.yml
services:
  web:
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "10"
        labels: "service=web,env=production"
```

**Sentry Integration (Error tracking):**

```bash
# Add to .env
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0

# Install Sentry SDK
pip install sentry-sdk

# In settings/prod.py
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    environment='production',
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
)
```

### UptimeRobot Monitoring

Configure external uptime monitoring:

1. Create UptimeRobot account at https://uptimerobot.com
2. Add new monitor:
   - **URL**: https://yourdomain.com/health/
   - **Type**: HTTPS
   - **Interval**: 5 minutes
   - **Alert contacts**: Your email/Slack/PagerDuty

3. Configure expected responses:
   - Status code: 200
   - Keyword: "healthy"

### Grafana Dashboards (Optional)

For advanced monitoring, setup Prometheus + Grafana:

```yaml
# docker-compose.yml additions
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
```

---

## Troubleshooting

### Common Production Issues

#### 1. Database Connection Failures

**Symptoms:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**
```bash
# Test database connectivity
psql -h <db-host> -U <db-user> -d ai_compliance_db

# Check Django database URL format
# Should be: postgres://user:password@host:5432/dbname?sslmode=require

# For Docker, check network:
docker network ls
docker network inspect compliance-network

# View database logs
docker compose logs postgres
```

**Common causes:**
- Database not running or reachable
- Firewall blocking port 5432
- Authentication failure (wrong password)
- Database doesn't exist yet (run migrations)

#### 2. Redis Connection Failures

**Symptoms:** `ConnectionError: Error 111 connecting to Redis`

**Solutions:**
```bash
# Test Redis connectivity
redis-cli -h <redis-host> -p 6379 ping

# Check Redis auth
redis-cli -h <redis-host> --auth <password> ping

# View Redis logs
docker compose logs redis

# Check REDIS_URL format
# Should be: redis://user:password@host:6379/0 or rediss:// for TLS
```

#### 3. Backblaze B2 Upload Timeouts

**Symptoms:** Celery task timeout during video upload

**Solutions:**
```bash
# Increase B2 retry settings in .env
B2_MAX_RETRIES=5
B2_RETRY_BACKOFF=2
B2_RETRY_BACKOFF_MAX=120

# Increase Celery timeout
CELERY_TASK_TIME_LIMIT=7200
CELERY_TASK_SOFT_TIME_LIMIT=6900

# Check B2 credentials
# Verify BACKBLAZE_ENDPOINT_URL is correct for your region

# Monitor uploads
docker compose logs -f celery-worker | grep -i "b2\|upload"
```

#### 4. SSL Certificate Issues

**Symptoms:** `NET::ERR_CERT_INVALID` or certificate expired

**Solutions:**
```bash
# Check certificate status
certbot certificates

# Force renewal (skip checks)
sudo certbot renew --force-renewal

# Check Nginx config references correct paths
sudo grep -n "ssl_certificate" /etc/nginx/sites-available/ai-compliance-agent

# Test SSL configuration
ssl-test yourdomain.com  # or use https://www.ssllabs.com/ssltest/

# Fix mixed content warnings
# Ensure all resources use https:// in templates
```

#### 5. Celery Tasks Not Processing

**Symptoms:** Tasks stuck in queue, not executing

**Solutions:**
```bash
# Check Celery worker status
sudo systemctl status ai-compliance-celery-worker.service

# Restart worker
sudo systemctl restart ai-compliance-celery-worker.service

# Check Redis connectivity
redis-cli PING

# View task queue
redis-cli LLEN celery:queue:celery

# Purge stuck tasks (⚠️ careful!)
celery -A backend.compliance_app purge

# View worker logs
sudo journalctl -u ai-compliance-celery-worker.service -n 100 -f
```

#### 6. Out of Disk Space

**Symptoms:** Migrations fail, uploads blocked, app crashes

**Solutions:**
```bash
# Check disk usage
df -h

# Find large files
du -sh /opt/ai-compliance-agent/*
du -sh /var/log/*

# Cleanup old logs
sudo journalctl --vacuum=7d

# Clean Docker artifacts
docker system prune -a

# Cleanup old backups
find /backups -name "*.sql.gz" -mtime +30 -delete
```

#### 7. Memory Leaks / High Memory Usage

**Symptoms:** Memory usage grows over time, services crash

**Solutions:**
```bash
# Monitor memory in real-time
watch free -h

# Set Celery max tasks per worker (restart worker between tasks)
CELERY_WORKER_MAX_TASKS_PER_CHILD=100

# Restart Gunicorn periodically
# Add to .env
GUNICORN_MAX_REQUESTS=1000

# Monitor with Docker stats
docker stats

# Check for memory leaks in logs
grep -i "memory\|out of memory" /var/log/ai-compliance-agent/*.log
```

#### 8. Slow API Response Times

**Symptoms:** API requests taking 5+ seconds

**Solutions:**
```bash
# Check database query performance
# Enable query logging in settings/prod.py
LOGGING = {
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {'handlers': ['console'], 'level': 'DEBUG'},
    }
}

# Analyze slow queries
# In PostgreSQL
SELECT query, calls, mean_exec_time FROM pg_stat_statements 
ORDER BY mean_exec_time DESC LIMIT 10;

# Optimize N+1 queries
# Use select_related() and prefetch_related() in Django ORM

# Add database indexes
# In migrations: db.execute("CREATE INDEX ... ON ...")
```

#### 9. Email Notifications Not Sending

**Symptoms:** No emails received, task completes silently

**Solutions:**
```bash
# Check SMTP settings in .env
# Verify EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

# Test email configuration manually
cd /opt/ai-compliance-agent
source venv/bin/activate
export $(cat .env | xargs)

python manage.py shell
from django.core.mail import send_mail
send_mail(
    'Test Subject',
    'Test message',
    'from@example.com',
    ['to@example.com']
)

# Check email backend
# For production: django.core.mail.backends.smtp.EmailBackend
# For console testing: django.core.mail.backends.console.EmailBackend

# Verify SMTP credentials (if Gmail)
# Use app-specific passwords, not account password
# Generate at: https://myaccount.google.com/apppasswords
```

#### 10. CloudFlare CDN Not Caching

**Symptoms:** B2 videos not served from CDN edge, high B2 egress costs

**Solutions:**
```bash
# Verify Cloudflare DNS records
# Should have CNAME: videos.yourdomain.com -> backblaze-cdn.yourdomain.com

# Check cache rules in Cloudflare dashboard
# TTL should be 24-48 hours for video content

# Purge cache
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

# Verify Content-Type headers are correct
# Videos should have Content-Type: video/mp4 (not text/plain)

# Test CDN with curl
curl -I https://cdn.yourdomain.com/video.mp4
# Look for: X-Cache: HIT from cloudflare
```

---

## Deployment Checklist

Before going live:

- [ ] Environment variables validated (`config_validator.py`)
- [ ] Database migrations completed and tested
- [ ] Static files collected and accessible
- [ ] SSL certificate installed and valid
- [ ] Email notifications tested
- [ ] Backups configured and tested
- [ ] Monitoring/health checks configured
- [ ] Log aggregation enabled
- [ ] Security headers configured in Nginx
- [ ] Rate limiting configured (optional)
- [ ] CORS configuration reviewed (if API access from browser)
- [ ] Performance tested under load
- [ ] Disaster recovery plan documented
- [ ] Team trained on incident response

---

## Additional Resources

- [Django Production Settings](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/index.html)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [PostgreSQL Performance](https://wiki.postgresql.org/wiki/Performance_Optimization)

---

---

## Русская версия

# Руководство по развертыванию AI-Комплаенс Агента в Production

Этот полный обзор охватывает развертывание AI-Комплаенс Агента в production-среду. Рассматриваются два пути развертывания:
1. **Docker/Docker Compose** (рекомендуется для управляемых платформ)
2. **Bare-metal с Gunicorn + systemd + Nginx** (для традиционных VPS/dedicated серверов)

## Содержание

1. [Предварительный чек-лист](#предварительный-чек-лист)
2. [Подготовка хоста](#подготовка-хоста)
3. [Управление секретами и конфигурацией](#управление-секретами-и-конфигурацией)
4. [Настройка окружения](#настройка-окружения)
5. [Путь развертывания 1: Docker Compose](#путь-развертывания-1-docker-compose)
6. [Путь развертывания 2: Bare-Metal Gunicorn + systemd + Nginx](#путь-развертывания-2-bare-metal-gunicorn--systemd--nginx)
7. [Миграции БД и сбор статики](#миграции-бд-и-сбор-статики)
8. [Сервисы Celery Worker & Beat](#сервисы-celery-worker--beat)
9. [Мониторинг и проверки здоровья](#мониторинг-и-проверки-здоровья)
10. [Решение проблем](#решение-проблем)

---

### Предварительный чек-лист

Перед развертыванием в production убедитесь, что у вас есть:

- [ ] Сгенерирован уникальный `SECRET_KEY`: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Провизионирована база данных PostgreSQL (v12+) с поддержкой SSL
- [ ] Провизионирован экземпляр Redis (v6+) с аутентификацией
- [ ] Учетная запись Backblaze B2 с:
  - [ ] Созданными ключами Application Key
  - [ ] Определенной S3-совместимой точкой доступа
  - [ ] Созданным бакетом для хранения видео
- [ ] Учетная запись Cloudflare (опционально, но рекомендуется) с:
  - [ ] Сконфигурированным DNS зоны
  - [ ] Сконфигурированным CNAME для бакета B2
  - [ ] Созданным API токеном
- [ ] SSL/TLS сертификат (Let's Encrypt или коммерческий)
- [ ] Сконфигурирована SMTP учетная запись (Gmail, SendGrid и т.д.)
- [ ] Доменное имя настроено и указывает на сервер
- [ ] Настроена агрегация логов сервера (опционально: Sentry, LogRocket и т.д.)

### Подготовка хоста

#### Для систем на основе Ubuntu/Debian

```bash
# Обновить пакеты системы
sudo apt-get update && sudo apt-get upgrade -y

# Установить системные зависимости
sudo apt-get install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  build-essential \
  curl \
  wget \
  git \
  ffmpeg \
  libmagic1 \
  libpq5 \
  ca-certificates \
  supervisor \
  nginx \
  certbot \
  python3-certbot-nginx

# Установить Docker (если используется Docker Compose развертывание)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установить Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Создайте пользователя приложения

```bash
# Создать непривилегированного пользователя для запуска приложения
sudo useradd -m -s /bin/bash -d /home/appuser appuser

# Добавить в группу sudo (опционально)
sudo usermod -aG sudo appuser
```

#### Создайте директории приложения

```bash
# От root или с sudo
sudo mkdir -p /opt/ai-compliance-agent
sudo mkdir -p /var/log/ai-compliance-agent
sudo mkdir -p /var/run/ai-compliance-agent
sudo chown -R appuser:appuser /opt/ai-compliance-agent /var/log/ai-compliance-agent /var/run/ai-compliance-agent
sudo chmod 755 /opt/ai-compliance-agent
```

### Управление секретами и конфигурацией

#### Вариант 1: Файл окружения (.env) - Простой подход

```bash
# Перейти в директорию приложения
cd /opt/ai-compliance-agent

# Скопировать пример конфигурации
cp .env.example .env

# Отредактировать с чувствительными значениями
nano .env

# Установить ограничительные права доступа
chmod 640 .env
sudo chown appuser:appuser .env
```

#### Вариант 2: Менеджер секретов - Корпоративный подход

Для больших развертываний используйте выделенный менеджер секретов.

#### Рекомендуемый: .env + Безопасное хранилище для ротации

Комбинируйте подходы для лучших практик:
1. Сохраняйте `.env` на сервере с ограничительными правами (640)
2. Используйте CI/CD для внедрения секретов в `.env` при развертывании
3. Реализуйте ротацию секретов через cron + hook CI/CD

### Настройка окружения

#### Задайте переменную DJANGO_ENV

Приложение использует модульные настройки на основе `DJANGO_ENV`:

```bash
# В файле .env или переменной окружения оболочки
export DJANGO_ENV=production

# Или добавьте в файл systemd service (см. ниже)
# Или добавьте в переменные окружения docker-compose
```

Это автоматически загружает `/backend/compliance_app/settings/prod.py` с:
- `DEBUG=False` (принудительно)
- Требование PostgreSQL
- Требование SMTP для email
- HTTPS перенаправления безопасности
- Строгие настройки CSRF и cookies

#### Валидируйте конфигурацию

Перед развертыванием запустите валидатор конфигурации:

```bash
cd /opt/ai-compliance-agent

# Загрузить окружение
export $(cat .env | xargs)

# Запустить валидатор
python backend/compliance_app/config_validator.py
```

Ожидаемый вывод:
```
============================================================
📋 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ КОНФИГУРАЦИИ
============================================================

✅ Конфигурация валидна! Все переменные заданы корректно.
```

#### Обязательные переменные окружения

Полный список см. в `.env.example`. Ключевые производственные переменные:

**Django Core:**
```
DJANGO_ENV=production
SECRET_KEY=<уникальный-безопасный-ключ>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,cdn.yourdomain.com
```

**База данных:**
```
DATABASE_URL=postgres://user:password@hostname:5432/dbname?sslmode=require
```

**Redis (с аутентификацией):**
```
REDIS_URL=rediss://default:password@hostname:6379/0
```

**Backblaze B2:**
```
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=<key-id>
BACKBLAZE_APPLICATION_KEY=<secret-key>
BACKBLAZE_BUCKET_NAME=ai-compliance-videos
```

**Cloudflare CDN (опционально):**
```
CLOUDFLARE_CDN_URL=https://cdn.yourdomain.com
CLOUDFLARE_ZONE_ID=<zone-id>
CLOUDFLARE_API_TOKEN=<api-token>
```

**Email уведомления:**
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-specific-password>
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
```

**Флаги безопасности:**
```
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### Путь развертывания 1: Docker Compose

#### Рекомендуется для:
- DigitalOcean App Platform
- AWS ECS с Docker Compose
- GCP Cloud Run
- Любого управляемого Docker хостинга
- Простых production установок

#### Предварительные требования

```bash
# Убедитесь, что Docker и Docker Compose установлены
docker --version  # Должна быть 20.10+
docker compose version  # Должна быть 2.0+
```

#### Установка

**1. Клонируйте репозиторий и сконфигурируйте:**

```bash
cd /opt/ai-compliance-agent
git clone <your-repo> .
cp .env.example .env

# Отредактируйте .env с производственными значениями
nano .env
```

**2. Запустите сервисы:**

```bash
# Получить последние образы
docker compose pull

# Запустить все сервисы (БД, redis, web, celery, celery-beat)
docker compose up -d

# Проверить здоровье
docker compose ps
docker compose logs web

# Дождитесь сообщения "Starting application"
docker compose logs --follow web | grep "Starting application"
```

**3. Запустите миграции:**

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
```

### Путь развертывания 2: Bare-Metal Gunicorn + systemd + Nginx

#### Рекомендуется для:
- Традиционного VPS (DigitalOcean Droplet, Linode, AWS EC2)
- On-premises серверов
- Ситуаций, требующих полного контроля
- Развертываний микросервисов

#### Предварительные требования

```bash
# Убедитесь, что системные пакеты установлены
python3.11 --version
nginx --version
systemctl --version
```

#### Установка

**1. Клонируйте репозиторий:**

```bash
cd /opt/ai-compliance-agent
git clone <your-repo> .
sudo chown -R appuser:appuser /opt/ai-compliance-agent
```

**2. Создайте виртуальное окружение Python:**

```bash
cd /opt/ai-compliance-agent
python3.11 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn[gevent]  # Production WSGI сервер

# Создать файл .env
cp .env.example .env
nano .env  # Отредактируйте с production значениями
```

**3. Запустите миграции и соберите статику:**

```bash
cd /opt/ai-compliance-agent

# Загрузить окружение
export $(cat .env | xargs)

# Запустить миграции
python backend/manage.py migrate

# Создать суперпользователя
python backend/manage.py createsuperuser

# Собрать статические файлы
python backend/manage.py collectstatic --noinput --clear
```

**4. Создайте файлы systemd service:**

**a) Gunicorn сервис (Django приложение):**

Создайте `/etc/systemd/system/ai-compliance-gunicorn.service`:

```ini
[Unit]
Description=AI-Compliance Agent - Gunicorn WSGI Server
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=appuser
WorkingDirectory=/opt/ai-compliance-agent
EnvironmentFile=/opt/ai-compliance-agent/.env

ExecStart=/opt/ai-compliance-agent/venv/bin/gunicorn \
    --workers=4 \
    --worker-class=gevent \
    --worker-connections=1000 \
    --timeout=120 \
    --access-logfile=/var/log/ai-compliance-agent/gunicorn-access.log \
    --error-logfile=/var/log/ai-compliance-agent/gunicorn-error.log \
    --bind=unix:/var/run/ai-compliance-agent/gunicorn.sock \
    backend.compliance_app.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**b) Celery Worker сервис:**

Создайте `/etc/systemd/system/ai-compliance-celery-worker.service`:

```ini
[Unit]
Description=AI-Compliance Agent - Celery Worker
After=network.target redis-server.service postgresql.service
Requires=ai-compliance-gunicorn.service

[Service]
Type=forking
User=appuser
WorkingDirectory=/opt/ai-compliance-agent
EnvironmentFile=/opt/ai-compliance-agent/.env

ExecStart=/opt/ai-compliance-agent/venv/bin/celery -A backend.compliance_app worker \
    --loglevel=info \
    --logfile=/var/log/ai-compliance-agent/celery-worker.log \
    --pidfile=/var/run/ai-compliance-agent/celery-worker.pid \
    --concurrency=4

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**c) Celery Beat сервис (периодические задачи):**

Создайте `/etc/systemd/system/ai-compliance-celery-beat.service`:

```ini
[Unit]
Description=AI-Compliance Agent - Celery Beat Scheduler
After=network.target redis-server.service postgresql.service
Requires=ai-compliance-gunicorn.service

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/ai-compliance-agent
EnvironmentFile=/opt/ai-compliance-agent/.env

ExecStart=/opt/ai-compliance-agent/venv/bin/celery -A backend.compliance_app beat \
    --loglevel=info \
    --logfile=/var/log/ai-compliance-agent/celery-beat.log \
    --pidfile=/var/run/ai-compliance-agent/celery-beat.pid \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**5. Включите и запустите сервисы:**

```bash
# Перезагрузить конфигурацию systemd
sudo systemctl daemon-reload

# Включить сервисы на автозагрузку
sudo systemctl enable ai-compliance-gunicorn.service
sudo systemctl enable ai-compliance-celery-worker.service
sudo systemctl enable ai-compliance-celery-beat.service

# Запустить сервисы
sudo systemctl start ai-compliance-gunicorn.service
sudo systemctl start ai-compliance-celery-worker.service
sudo systemctl start ai-compliance-celery-beat.service

# Проверить статус
sudo systemctl status ai-compliance-gunicorn.service
sudo systemctl status ai-compliance-celery-worker.service
sudo systemctl status ai-compliance-celery-beat.service

# Просмотреть логи
sudo journalctl -u ai-compliance-gunicorn.service -f
sudo journalctl -u ai-compliance-celery-worker.service -f
sudo journalctl -u ai-compliance-celery-beat.service -f
```

**6. Сконфигурируйте Nginx (обратный прокси + TLS):**

Создайте `/etc/nginx/sites-available/ai-compliance-agent`:

```nginx
# Перенаправить HTTP на HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # Let's Encrypt валидация
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Перенаправить весь остальной трафик на HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Основной HTTPS сервер
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL сертификат (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL конфигурация (Modern)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Заголовки безопасности
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Логирование
    access_log /var/log/ai-compliance-agent/nginx-access.log;
    error_log /var/log/ai-compliance-agent/nginx-error.log;

    # Размер загрузки клиента
    client_max_body_size 2G;

    # Gzip сжатие
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_vary on;
    gzip_min_length 1000;

    # Статические файлы (обслуживаются прямо Nginx)
    location /static/ {
        alias /opt/ai-compliance-agent/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Медиа файлы (обслуживаются прямо Nginx или прокси на B2)
    location /media/ {
        alias /opt/ai-compliance-agent/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Прокси на Gunicorn
    location / {
        proxy_pass http://unix:/var/run/ai-compliance-agent/gunicorn.sock;
        proxy_http_version 1.1;
        
        # Заголовки
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Буферизация
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Поддержка WebSocket (для будущих возможностей реального времени)
    location /ws/ {
        proxy_pass http://unix:/var/run/ai-compliance-agent/gunicorn.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Конечная точка проверки здоровья
    location /health/ {
        proxy_pass http://unix:/var/run/ai-compliance-agent/gunicorn.sock;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        access_log off;
    }
}
```

Включите сайт Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/ai-compliance-agent /etc/nginx/sites-enabled/

# Тестировать конфигурацию
sudo nginx -t

# Запустить/перезагрузить Nginx
sudo systemctl start nginx
sudo systemctl reload nginx
```

**7. Настройте Let's Encrypt SSL сертификат:**

```bash
# Установить сертификат
sudo certbot certonly --webroot -w /var/www/certbot \
    -d yourdomain.com -d www.yourdomain.com \
    --agree-tos --email admin@yourdomain.com

# Настроить автоматическое обновление
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Тестировать обновление (dry-run)
sudo certbot renew --dry-run

# Проверить лог обновления
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Миграции БД и сбор статики

#### Запуск миграций

**Docker Compose:**
```bash
docker compose exec web python manage.py migrate --noinput
```

**Bare-metal:**
```bash
cd /opt/ai-compliance-agent
source venv/bin/activate
export $(cat .env | xargs)

python backend/manage.py migrate --noinput
```

#### Сбор статических файлов

Это обрабатывается автоматически скриптом `scripts/entrypoint.sh` в Docker и сервисом systemd в bare-metal.

Для ручного сбора статики:

```bash
# Docker Compose
docker compose exec web python manage.py collectstatic --noinput --clear

# Bare-metal
cd /opt/ai-compliance-agent/backend
python manage.py collectstatic --noinput --clear
```

#### Django Check для Production

Всегда проверяйте конфигурацию production перед запуском:

```bash
# Docker Compose
docker compose exec web python manage.py check --deploy

# Bare-metal
cd /opt/ai-compliance-agent
source venv/bin/activate
export $(cat .env | xargs)

python backend/manage.py check --deploy
```

### Сервисы Celery Worker & Beat

#### Архитектура

- **Celery Worker**: Обрабатывает асинхронные задачи (обработка видео, AI инференс, компиляция отчетов)
- **Celery Beat**: Запускает периодические задачи (очистка, обновление кэша CDN)
- **Redis**: Брокер сообщений и backend результатов

#### Конфигурация

Ключевые настройки в `.env`:

```bash
# Параллелизм Celery (количество параллельных задач)
CELERY_WORKER_CONCURRENCY=4

# Макс задач на worker перед перезагрузкой
CELERY_WORKER_MAX_TASKS_PER_CHILD=100

# Таймауты задач
CELERY_TASK_TIME_LIMIT=3600       # 1 час жесткий лимит
CELERY_TASK_SOFT_TIME_LIMIT=3300  # 55 мин мягкое предупреждение
```

#### Запуск сервисов

**Docker Compose (автоматизировано):**
```bash
docker compose up -d celery-worker celery-beat
docker compose logs -f celery-worker celery-beat
```

**Bare-metal (systemd):**
```bash
sudo systemctl start ai-compliance-celery-worker.service
sudo systemctl start ai-compliance-celery-beat.service

# Мониторить
sudo journalctl -u ai-compliance-celery-worker.service -f
```

### Мониторинг и проверки здоровья

#### Конечная точка проверки здоровья приложения

Приложение предоставляет конечную точку проверки здоровья:

```bash
# Запросить здоровье
curl https://yourdomain.com/health/

# Ответ (JSON)
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "workers: 1, tasks: 0"
}
```

### Решение проблем

#### 1. Ошибки подключения к БД

**Признаки:** `psycopg2.OperationalError: could not connect to server`

**Решения:**
```bash
# Тестировать подключение к БД
psql -h <db-host> -U <db-user> -d ai_compliance_db

# Проверить формат URL БД Django
# Должно быть: postgres://user:password@host:5432/dbname?sslmode=require

# Для Docker, проверить сеть:
docker network ls
docker network inspect compliance-network

# Просмотреть логи БД
docker compose logs postgres
```

#### 2. Ошибки подключения к Redis

**Признаки:** `ConnectionError: Error 111 connecting to Redis`

**Решения:**
```bash
# Тестировать подключение Redis
redis-cli -h <redis-host> -p 6379 ping

# Проверить аутентификацию Redis
redis-cli -h <redis-host> --auth <password> ping

# Просмотреть логи Redis
docker compose logs redis

# Проверить формат REDIS_URL
# Должно быть: redis://user:password@host:6379/0 или rediss:// для TLS
```

#### 3. Таймауты загрузки Backblaze B2

**Признаки:** Таймаут задачи Celery при загрузке видео

**Решения:**
```bash
# Увеличить настройки повторных попыток B2 в .env
B2_MAX_RETRIES=5
B2_RETRY_BACKOFF=2
B2_RETRY_BACKOFF_MAX=120

# Увеличить таймаут Celery
CELERY_TASK_TIME_LIMIT=7200
CELERY_TASK_SOFT_TIME_LIMIT=6900

# Проверить учетные данные B2
# Проверить что BACKBLAZE_ENDPOINT_URL верен для вашего региона

# Мониторить загрузки
docker compose logs -f celery-worker | grep -i "b2\|upload"
```

#### 4. Проблемы SSL сертификата

**Признаки:** `NET::ERR_CERT_INVALID` или истекший сертификат

**Решения:**
```bash
# Проверить статус сертификата
certbot certificates

# Принудительное обновление
sudo certbot renew --force-renewal

# Проверить что конфиг Nginx ссылается на правильные пути
sudo grep -n "ssl_certificate" /etc/nginx/sites-available/ai-compliance-agent

# Тестировать конфигурацию SSL
ssl-test yourdomain.com  # или используйте https://www.ssllabs.com/ssltest/
```

---

## Чек-лист развертывания

Перед запуском:

- [ ] Переменные окружения валидированы (`config_validator.py`)
- [ ] Миграции БД завершены и протестированы
- [ ] Статические файлы собраны и доступны
- [ ] SSL сертификат установлен и действителен
- [ ] Email уведомления протестированы
- [ ] Резервные копии сконфигурированы и протестированы
- [ ] Мониторинг/проверки здоровья сконфигурированы
- [ ] Агрегация логов включена
- [ ] Заголовки безопасности сконфигурированы в Nginx
- [ ] Ограничение скорости сконфигурировано (опционально)
- [ ] CORS конфигурация проверена (если доступ API из браузера)
- [ ] Производительность протестирована под нагрузкой
- [ ] План восстановления при аварии документирован
- [ ] Команда обучена реагированию на инциденты

---

