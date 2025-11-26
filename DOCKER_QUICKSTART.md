# 🐳 Docker Quick Start Guide

Get AI-Compliance Agent running locally with Docker Compose in 5 minutes.

## Prerequisites

- Docker Engine 20.10+ and Docker Compose V2
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

## Quick Start

### 1. Clone and Configure

```bash
# Navigate to project directory
cd ai-compliance-agent

# Create environment file for Docker
cp .env.docker .env

# (Optional) Edit configuration
nano .env
```

### 2. Start Services

```bash
# Start all services in background
docker compose up -d

# View logs (optional)
docker compose logs -f
```

Services starting:
- PostgreSQL (database)
- Redis (Celery broker)
- MinIO (local S3-compatible storage)
- Django web server
- Celery worker
- Celery beat

### 3. Initialize Database

```bash
# Run migrations (wait ~30 seconds for DB to be ready)
docker compose exec web python manage.py migrate

# Create admin user
docker compose exec web python manage.py createsuperuser
```

### 4. Access Application

- **Main app**: http://localhost:8000
- **Admin panel**: http://localhost:8000/admin
- **API docs**: http://localhost:8000/api/docs/
- **MinIO console**: http://localhost:9001 (user: `minioadmin`, pass: `minioadmin`)

### 5. Create MinIO Bucket

```bash
# Option A: Via Web UI
# Open http://localhost:9001
# Login: minioadmin / minioadmin
# Create bucket: ai-compliance-videos

# Option B: Via Docker exec
docker compose exec web python << END
from storage.backblaze import BackblazeService
service = BackblazeService()
service.create_bucket_if_not_exists()
END
```

## Common Commands

### Service Management

```bash
# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes all data)
docker compose down -v

# Restart specific service
docker compose restart web
docker compose restart celery-worker

# View service status
docker compose ps

# View logs
docker compose logs web
docker compose logs celery-worker
docker compose logs -f  # Follow all logs
```

### Django Management

```bash
# Run any Django command
docker compose exec web python manage.py <command>

# Examples:
docker compose exec web python manage.py shell
docker compose exec web python manage.py test
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py migrate
```

### Celery Commands

```bash
# Check Celery worker status
docker compose exec celery-worker celery -A compliance_app inspect active

# Check scheduled tasks
docker compose exec celery-worker celery -A compliance_app inspect scheduled

# Purge all tasks
docker compose exec celery-worker celery -A compliance_app purge
```

### Database Access

```bash
# PostgreSQL shell
docker compose exec postgres psql -U postgres -d ai_compliance_db

# Django dbshell
docker compose exec web python manage.py dbshell

# Backup database
docker compose exec postgres pg_dump -U postgres ai_compliance_db > backup.sql

# Restore database
cat backup.sql | docker compose exec -T postgres psql -U postgres ai_compliance_db
```

### Development Workflow

```bash
# Edit code in backend/ directory
# Changes are live-reloaded (volume mounted)

# Rebuild after dependency changes
docker compose up -d --build

# Run tests
docker compose exec web python manage.py test

# Check for issues
docker compose exec web python manage.py check
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Stop conflicting service or change port in docker-compose.yml
```

### Database Not Ready

```bash
# Check PostgreSQL logs
docker compose logs postgres

# Wait for healthy status
docker compose ps | grep postgres

# Manually restart in order
docker compose down
docker compose up -d postgres redis minio
sleep 10
docker compose up -d web celery-worker celery-beat
```

### Celery Worker Not Processing

```bash
# Check worker logs
docker compose logs celery-worker

# Verify Redis connection
docker compose exec redis redis-cli ping

# Restart worker
docker compose restart celery-worker
```

### Permission Denied Errors

```bash
# Fix ownership (Linux/macOS)
sudo chown -R $USER:$USER .

# Or run with sudo
sudo docker compose up -d
```

### Cannot Connect to Docker Daemon

```bash
# Start Docker service
sudo systemctl start docker  # Linux
# Or start Docker Desktop (macOS/Windows)

# Check Docker status
docker info
```

## Production Deployment

**⚠️ Note**: This docker-compose.yml is for **development only**.

For production:
1. Use `.env.example` (not `.env.docker`)
2. Set `DJANGO_ENV=production`
3. Use managed PostgreSQL/Redis services
4. Use Backblaze B2 (not MinIO)
5. Enable HTTPS and security settings
6. See [DEPLOYMENT.md](DEPLOYMENT.md) for full guide

## Clean Up

```bash
# Stop and remove containers
docker compose down

# Remove volumes (⚠️ deletes all data)
docker compose down -v

# Remove images
docker rmi ai-compliance-agent-web
docker rmi ai-compliance-agent-celery-worker
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Review [CONFIGURATION.md](CONFIGURATION.md) for settings
- See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [API_HTMX_DOCUMENTATION.md](API_HTMX_DOCUMENTATION.md) for API usage

---

**Need help?** Check the [Troubleshooting section in DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting)
