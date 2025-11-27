# Development Guide

This guide covers local development workflows for the AI Compliance Agent system. Whether you're developing with Docker Compose or a traditional local setup, this document walks you through the entire process.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Development with Docker Compose](#development-with-docker-compose)
4. [Development Without Docker](#development-without-docker)
5. [Testing](#testing)
6. [Code Quality](#code-quality)
7. [Makefile Shortcuts](#makefile-shortcuts)
8. [Debugging & Troubleshooting](#debugging--troubleshooting)
9. [Seeding Data](#seeding-data)
10. [Accessing Local Services](#accessing-local-services)
11. [Common Development Tasks](#common-development-tasks)

---

## Prerequisites

### System Requirements

Before starting development, ensure you have:

- **Python 3.11+** - Check with: `python --version`
- **PostgreSQL** (if not using Docker) - `postgres --version`
- **Redis** (if not using Docker) - `redis-cli --version`
- **Docker & Docker Compose** (for containerized development):
  - Install Docker: https://docs.docker.com/get-docker/
  - Verify with: `docker --version` and `docker compose --version`
- **Git** - `git --version`
- **curl** or **wget** - For testing API endpoints

### macOS/Linux System Packages

```bash
# macOS with Homebrew
brew install python@3.11 postgresql redis docker-desktop

# Ubuntu/Debian
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
  postgresql-client redis-tools docker.io docker-compose

# Fedora/RHEL
sudo dnf install -y python3.11 python3.11-devel postgresql-libs redis docker docker-compose
```

### Windows

- Install Python 3.11 from https://www.python.org/downloads/
- Install PostgreSQL from https://www.postgresql.org/download/windows/
- Install Docker Desktop from https://docs.docker.com/desktop/install/windows-install/
- Use Windows Subsystem for Linux 2 (WSL2) for best Docker experience
- Or use Git Bash for shell commands

---

## Environment Setup

### 1. Clone & Navigate to Repository

```bash
git clone <repository-url>
cd ai-compliance-agent
git checkout docs-development-guide  # Switch to development branch
```

### 2. Create Environment Configuration

Two options:

**Option A: Using `setup_env.sh` (Recommended)**

```bash
chmod +x setup_env.sh
./setup_env.sh
# Follow prompts to overwrite .env if needed
```

**Option B: Manual Setup**

```bash
# Copy example configuration
cp .env.example .env

# For Docker development, you can use pre-configured Docker settings
cp .env.docker .env  # Alternative for Docker Compose
```

### 3. Choose Your DJANGO_ENV

Edit `.env` and set:

```bash
# For local development (easiest)
DJANGO_ENV=development

# For production-like testing (with security checks)
DJANGO_ENV=production
```

**Differences:**
- `development`: DEBUG=True, SQLite by default, console email, no HTTPS redirect
- `production`: DEBUG=False, PostgreSQL required, SMTP required, strict security

### 4. Configure Required Variables

**For Development (minimal setup):**

```bash
# .env file (development mode)
DJANGO_ENV=development
DEBUG=True
SECRET_KEY=your-development-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3  # SQLite for simple dev
REDIS_URL=redis://localhost:6379/0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Dummy tokens for testing (won't actually call these services)
REPLICATE_API_TOKEN=test_token_123
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=test_key_id
BACKBLAZE_APPLICATION_KEY=test_key
BACKBLAZE_BUCKET_NAME=test-bucket
```

**For Docker Development (comes pre-configured):**

The `.env.docker` file is already optimized for Docker Compose with:
- PostgreSQL in Docker
- Redis in Docker
- MinIO (S3-compatible) for local storage testing
- Console email backend
- Dummy API tokens

### 5. Validate Configuration

```bash
python backend/compliance_app/config_validator.py
```

Expected output:
```
✅ Configuration is valid! All variables are set correctly.
```

If you see errors, check the error messages and update `.env` accordingly.

---

## Development with Docker Compose

### 1. Start All Services

```bash
# Copy Docker configuration to .env
cp .env.docker .env

# Build and start all services (PostgreSQL, Redis, MinIO, Django, Celery)
docker compose up -d

# Watch logs in real-time
docker compose logs -f

# Stop with Ctrl+C, then cleanup
docker compose down
```

### 2. Services Overview

When you run `docker compose up`, the following services start:

| Service | Port | Purpose | URL |
|---------|------|---------|-----|
| `web` | 8000 | Django web app | http://localhost:8000 |
| `celery-worker` | N/A | Task queue worker | Manages background jobs |
| `celery-beat` | N/A | Task scheduler | Periodic jobs |
| `postgres` | 5432 | Database | `postgres://postgres:postgres@localhost:5432/ai_compliance_db` |
| `redis` | 6379 | Cache & broker | `redis://localhost:6379/0` |
| `minio` | 9000/9001 | S3-compatible storage | http://localhost:9001 (console) |

### 3. Common Docker Compose Commands

```bash
# Start services (detached mode)
docker compose up -d

# Start services with live logs
docker compose up

# View logs for all services
docker compose logs -f

# View logs for specific service
docker compose logs -f web
docker compose logs -f celery-worker

# Execute command in web container
docker compose exec web bash
docker compose exec web python manage.py shell

# Stop all services
docker compose stop

# Stop and remove containers (data persists in volumes)
docker compose down

# Stop and remove containers + volumes (WARNING: deletes all data!)
docker compose down -v

# Restart specific service
docker compose restart web
docker compose restart celery-worker

# Rebuild images (if Dockerfile changed)
docker compose build
```

### 4. Database Migrations in Docker

```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# Check migration status
docker compose exec web python manage.py showmigrations

# Reverse a migration
docker compose exec web python manage.py migrate projects 0001
```

### 5. Access Services in Docker

**Web Application:**
```bash
open http://localhost:8000
# or
curl http://localhost:8000
```

**Database Shell:**
```bash
docker compose exec postgres psql -U postgres -d ai_compliance_db

# List tables
\dt

# Exit
\q
```

**Redis CLI:**
```bash
docker compose exec redis redis-cli

# Check keys
KEYS *

# Exit
EXIT
```

**MinIO Console (S3 Storage):**
```
http://localhost:9001
Username: minioadmin
Password: minioadmin
```

### 6. Troubleshooting Docker Compose

**Services won't start:**
```bash
# Check for port conflicts
netstat -tuln | grep -E "8000|5432|6379|9000"

# Free port if needed (example for port 8000)
# macOS/Linux
lsof -i :8000 | grep -v COMMAND | awk '{print $2}' | xargs kill -9

# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
```

**Container crashes or fails to start:**
```bash
# Check Docker logs for errors
docker compose logs web

# Try rebuilding and restarting
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

**Database connection errors:**
```bash
# Ensure PostgreSQL is healthy
docker compose exec postgres pg_isready -U postgres

# Recreate PostgreSQL volume
docker compose down -v
docker compose up -d postgres
# Wait 10 seconds for postgres to start
sleep 10
docker compose up -d
```

---

## Development Without Docker

For local development without Docker, follow these steps:

### 1. Create Python Virtual Environment

```bash
# Create venv
python3.11 -m venv venv

# Activate venv
# macOS/Linux
source venv/bin/activate

# Windows CMD
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (pytest, black, flake8, etc.)
pip install -r requirements.dev.txt
```

### 3. Configure Local Environment

```bash
# Copy and configure .env for local development
cp .env.example .env

# Edit .env with these minimal values
export DJANGO_ENV=development
export DATABASE_URL=sqlite:///db.sqlite3
export REDIS_URL=redis://localhost:6379/0
export EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
export SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
export REPLICATE_API_TOKEN=test_token_123

# Or create .env file with these settings
cat > .env << 'EOF'
DJANGO_ENV=development
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,.local
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
REPLICATE_API_TOKEN=test_token
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=test_id
BACKBLAZE_APPLICATION_KEY=test_key
BACKBLAZE_BUCKET_NAME=test-bucket
EOF
```

### 4. Start Redis (Required)

Redis is required for Celery task queue. Start it before running the app:

```bash
# macOS with Homebrew
brew services start redis

# Ubuntu/Debian with systemd
sudo systemctl start redis-server

# Manual start (any OS)
redis-server
```

Check Redis is running:
```bash
redis-cli ping
# Should output: PONG
```

### 5. Run Migrations

```bash
cd backend
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 7. Collect Static Files (Optional)

```bash
python manage.py collectstatic --noinput
```

### 8. Run Development Server

In one terminal:
```bash
cd backend
python manage.py runserver
```

Access at http://localhost:8000

### 9. Run Celery Worker (in separate terminal)

In a **new terminal**, activate venv first:

```bash
# Activate venv
source venv/bin/activate  # macOS/Linux
# or venv\Scripts\activate.bat  # Windows

# Start Celery worker
cd backend
celery -A compliance_app worker --loglevel=info
```

### 10. Run Celery Beat (Optional, for scheduled tasks)

In a **third terminal**:

```bash
# Activate venv
source venv/bin/activate

# Start Celery Beat
cd backend
celery -A compliance_app beat --loglevel=info
```

---

## Testing

### Running Tests with Django Test Runner

```bash
cd backend

# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test projects
python manage.py test ai_pipeline
python manage.py test operators

# Run specific test class
python manage.py test projects.tests.ProjectTests

# Run specific test method
python manage.py test projects.tests.ProjectTests.test_create_project

# Verbose output
python manage.py test -v 2

# Stop on first failure
python manage.py test --failfast
```

### Running Tests with pytest (if installed)

```bash
# Install pytest and plugins
pip install pytest pytest-django pytest-cov

# Run all tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Run tests matching pattern
pytest -k test_video

# Run specific file
pytest projects/tests_api_htmx.py

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Generate Coverage Report

```bash
# Using pytest
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows
```

### Running Tests in Docker

```bash
# Run tests in web container
docker compose exec web python manage.py test

# Run with coverage
docker compose exec web pytest --cov=. --cov-report=term
```

---

## Code Quality

### Linting with flake8

```bash
# Check all Python files
flake8 backend/

# Show statistics
flake8 backend/ --statistics

# Check specific file
flake8 backend/projects/models.py
```

### Code Formatting with black

```bash
# Format all files
black backend/

# Check without formatting
black backend/ --check

# Format specific file
black backend/projects/models.py
```

### Import Sorting with isort

```bash
# Sort imports
isort backend/

# Check without modifying
isort backend/ --check-only
```

### Django System Checks

```bash
cd backend

# Run all checks
python manage.py check

# Check for production-ready settings
python manage.py check --deploy

# Check specific app
python manage.py check --tag=security
```

### Type Checking (Optional)

```bash
# If mypy installed
pip install mypy django-stubs

# Type check backend
mypy backend/
```

### Run All Quality Checks

```bash
# Using Makefile
make check        # Django checks
make lint         # flake8
make format       # black + isort
make test         # Run tests

# Or individually
cd backend && python manage.py check --deploy && \
flake8 backend/ && \
black backend/ && \
isort backend/ && \
python manage.py test
```

---

## Makefile Shortcuts

The project includes a `Makefile` with common development commands:

```bash
# Show all available commands
make help

# Installation
make install       # Install production dependencies
make dev-install   # Install dev dependencies

# Development
make migrate       # Run database migrations
make makemigrations # Create new migrations
make shell         # Open Django shell
make superuser     # Create superuser
make collectstatic # Collect static files
make runserver     # Run development server

# Testing & Quality
make test          # Run tests
make test-coverage # Run tests with coverage
make lint          # Run flake8
make format        # Format code (black + isort)
make check         # Run Django system checks
make validate-config # Validate environment config

# Docker
make docker-build  # Build Docker images
make docker-up     # Start all services
make docker-down   # Stop all services
make docker-logs   # View logs
make docker-shell  # Open shell in web container
make docker-migrate # Run migrations in Docker

# Cleanup
make clean         # Remove __pycache__, .pyc files
make clean-docker  # Remove Docker volumes (WARNING: deletes data!)

# Celery (local development)
make celery-worker # Start Celery worker
make celery-beat   # Start Celery Beat scheduler
```

---

## Debugging & Troubleshooting

### Django Shell

Interactive Python shell with Django context:

```bash
cd backend
python manage.py shell

# Create an object
from projects.models import Project
p = Project.objects.create(name="Test", organization="TestOrg")

# Query
projects = Project.objects.filter(organization="TestOrg")
print(projects.count())

# Exit
exit()
```

### Print Debugging

Add print statements in code and check logs:

```python
# In views.py or models.py
print("DEBUG: Video ID =", video_id)
print("DEBUG: Triggers =", triggers)
```

View in Django logs:
```bash
python manage.py runserver  # Prints to console
```

### Pdb Debugger

```python
# In Python code
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

When execution hits the breakpoint, you'll enter interactive debugger:
```bash
(Pdb) n            # Next line
(Pdb) s            # Step into function
(Pdb) c            # Continue execution
(Pdb) p variable   # Print variable
(Pdb) l            # List code
(Pdb) h            # Help
```

### SQL Query Logging

```bash
# In .env or settings
LOG_SQL_QUERIES=True
```

Then in Django shell:
```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as context:
    projects = Project.objects.all()

for query in context:
    print(query['sql'])
```

### View HTTP Headers and Response

```python
# In test or shell
from django.test import Client

client = Client()
response = client.get('/api/projects/')

print("Status:", response.status_code)
print("Headers:", response)
print("Content:", response.json())
```

### Common Issues

**"ModuleNotFoundError: No module named 'django'"**
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

**"PostgreSQL connection refused"**
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Linux
```

**"Redis connection refused"**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis
brew services start redis  # macOS
sudo systemctl start redis-server  # Linux
```

**"Port already in use"**
```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>

# Or use different port
python manage.py runserver 8001
```

**"ModuleNotFoundError: No module named 'compliance_app.settings'"**
```bash
# Ensure DJANGO_SETTINGS_MODULE is set or use .env
export DJANGO_SETTINGS_MODULE=compliance_app.settings
# or cd backend first
cd backend
python manage.py check
```

---

## Seeding Data

### Django Fixtures

Create sample data via Django shell:

```bash
cd backend
python manage.py shell
```

```python
from users.models import User, UserRole
from projects.models import Project

# Create a client user
client = User.objects.create_user(
    username='client@example.com',
    email='client@example.com',
    password='password123',
    role=UserRole.CLIENT
)

# Create a project
project = Project.objects.create(
    name='Sample Project',
    organization='Sample Org',
    owner=client
)

print(f"Created project: {project}")
exit()
```

### Dump Data to Fixture

```bash
cd backend

# Dump all data
python manage.py dumpdata > fixtures/initial_data.json

# Dump specific app
python manage.py dumpdata projects > fixtures/projects.json

# Dump specific model
python manage.py dumpdata projects.Project > fixtures/projects.json

# Load data from fixture
python manage.py loaddata fixtures/initial_data.json
```

### Reset Database

```bash
cd backend

# Delete all data (flush) and rebuild
python manage.py flush
python manage.py migrate
python manage.py createsuperuser
```

---

## Accessing Local Services

### Django HTMX Dashboard

**URL:** http://localhost:8000/client/dashboard/

**Login:**
1. Use superuser credentials created via `python manage.py createsuperuser`
2. Access dashboard to upload videos, manage projects, view reports

**Features:**
- Project management (create/edit/delete)
- Video upload with progress tracking
- Pipeline execution monitoring
- Report viewing and download

### Django REST Framework (DRF) API Docs

**Swagger UI:** http://localhost:8000/api/docs/

**ReDoc:** http://localhost:8000/api/redoc/

**OpenAPI Schema:** http://localhost:8000/api/schema/

**Features:**
- Interactive API testing
- Try-it-out functionality
- Schema documentation
- Authentication token generation

### Admin Panel

**URL:** http://localhost:8000/admin/

**Features:**
- Manage users, projects, videos
- Monitor pipeline executions
- View error logs
- Manage AI triggers and risk definitions

### Testing API Endpoints

```bash
# Get JWT token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"password123"}' \
  | jq -r '.access')

# Query projects
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/projects/

# Create a project
curl -X POST http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","organization":"TestOrg"}'

# View API schema
curl http://localhost:8000/api/schema/ | jq .
```

### Celery Task Monitoring

```bash
# Inspect active tasks
celery -A compliance_app inspect active

# View task stats
celery -A compliance_app inspect stats

# Purge all pending tasks
celery -A compliance_app purge

# Monitor tasks in real-time
celery -A compliance_app events
```

---

## Common Development Tasks

### Add a New Django App

```bash
cd backend

# Create app
python manage.py startapp myapp

# Create models in myapp/models.py
# Add app to settings
# Create migrations
python manage.py makemigrations
python manage.py migrate
```

### Create a Database Migration

```bash
cd backend

# After modifying models.py
python manage.py makemigrations

# Review migration file in migrations/
# Apply migration
python manage.py migrate

# Reverse migration if needed
python manage.py migrate myapp 0001
```

### Add New Dependencies

```bash
# Add to requirements.txt or requirements.dev.txt
echo "new-package==1.0.0" >> requirements.txt

# Install locally
pip install new-package==1.0.0

# For Docker, rebuild image
docker compose build
docker compose up -d
```

### Create a Celery Task

```python
# In ai_pipeline/celery_tasks.py
from celery import shared_task

@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    time_limit=3600,
    soft_time_limit=3300
)
def my_task(param1, param2):
    # Task logic
    return result

# Call from view/signal
my_task.delay(param1="value1", param2="value2")
```

### Modify Environment Variables

```bash
# Edit .env file
nano .env

# For Docker, rebuild if needed
docker compose down
docker compose build
docker compose up -d

# For local development, changes apply immediately
```

### Monitor Celery Tasks in Docker

```bash
# View worker logs
docker compose logs -f celery-worker

# Check active tasks
docker compose exec celery-worker celery -A compliance_app inspect active

# Purge pending tasks
docker compose exec celery-worker celery -A compliance_app purge
```

---

## Performance Optimization Tips

### Disable Debug Toolbar in Production

Debug Toolbar adds overhead. Ensure it's off:

```bash
export DJANGO_ENV=production
```

### Database Query Optimization

```python
# Use select_related for foreign keys
projects = Project.objects.select_related('owner').all()

# Use prefetch_related for reverse foreign keys/many-to-many
videos = Video.objects.prefetch_related('triggers').all()
```

### Cache Frequently Accessed Data

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def my_view(request):
    # ...
```

### Use Connection Pooling

For PostgreSQL, enable pgBouncer or similar in production (configured in DEPLOYMENT.md).

---

## Further Reading

- **[docs/CONFIGURATION.md](../CONFIGURATION.md)** - Environment variable reference
- **[docs/DEPLOYMENT.md](../DEPLOYMENT.md)** - Production deployment guide
- **[docs/ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture overview
- **[docs/API.md](./API.md)** - API and HTMX interface documentation
- **[README.md](../README.md)** - Project overview

---

## Getting Help

### Check Logs

```bash
# Django development server logs (console output)
python manage.py runserver

# Celery worker logs
celery -A compliance_app worker --loglevel=debug

# Docker logs
docker compose logs -f <service_name>

# Docker logs for specific service
docker compose logs -f web
docker compose logs -f celery-worker
```

### Validate Configuration

```bash
python backend/compliance_app/config_validator.py
```

### Django System Checks

```bash
cd backend
python manage.py check --deploy
```

### Run Tests with Verbose Output

```bash
cd backend
python manage.py test -v 2 --failfast
```

---

**Happy developing! 🚀**

For questions or issues, check [docs/ARCHITECTURE.md](./ARCHITECTURE.md) and [docs/API.md](./API.md) for more details on the system design and API usage.
