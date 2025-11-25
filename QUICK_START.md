# Quick Start Guide

This guide provides quick instructions for testing and deploying the AI Compliance Agent.

## 🧪 Running Tests

### Prerequisites
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run All Tests
```bash
cd backend
python manage.py test --verbosity=2
```

### Run Specific App Tests
```bash
# Users app
python manage.py test users --verbosity=2

# Projects app
python manage.py test projects --verbosity=2

# AI Pipeline app
python manage.py test ai_pipeline --verbosity=2

# Operators app
python manage.py test operators --verbosity=2

# Admins app
python manage.py test admins --verbosity=2

# Storage app
python manage.py test storage --verbosity=2
```

### Run Tests with Coverage
```bash
# Install coverage
pip install coverage

# Run tests with coverage
cd backend
coverage run --source='.' manage.py test
coverage report
coverage html  # Open htmlcov/index.html in browser
```

### Test Categories

#### Unit Tests
- Model methods and properties
- Form validation
- View logic
- Permission checks

#### Integration Tests
- Complete AI pipeline workflow
- User role-based access
- File upload and processing
- Database relationships

#### Performance Tests
```bash
# Install Locust for load testing
pip install locust

# Run load tests
locust -f tests/load_tests.py --host=http://localhost:8000
```

## 🚀 Local Development Setup

### 1. Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd ai-compliance-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required minimum settings for development:**
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
```

### 3. Database Setup
```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Services
```bash
# Terminal 1: Django server
cd backend
python manage.py runserver

# Terminal 2: Celery worker
cd backend
celery -A compliance_app worker --loglevel=info

# Terminal 3: Redis (if not running)
redis-server
```

### 5. Access Application
- Main app: http://localhost:8000
- Admin panel: http://localhost:8000/admin
- API documentation: http://localhost:8000/api/docs/

## 🐳 Docker Deployment

### Development Docker
```bash
# Build image
docker build -t ai-compliance-agent .

# Run with docker-compose
docker-compose up -d
```

### Production Docker
```bash
# Build production image
docker build -f Dockerfile.prod -t ai-compliance-agent:prod .

# Run with production compose
docker-compose -f docker-compose.prod.yml up -d
```

## ☁️ Cloud Deployment

### DigitalOcean App Platform

#### 1. Prepare Repository
```bash
# Ensure .env.example is complete
git add .env.example
git commit -m "Add environment template"

# Push to GitHub
git push origin main
```

#### 2. Create App
1. Go to DigitalOcean Control Panel
2. Create new App
3. Connect GitHub repository
4. Configure components:
   - Web Service (Django)
   - Worker (Celery)
   - Database (PostgreSQL)
   - Redis (Managed Redis)

#### 3. Environment Variables
Set these in DigitalOcean App Platform:
```bash
# Core
DEBUG=False
SECRET_KEY=production-secret-key
ALLOWED_HOSTS=your-app-name.ondigitalocean.app

# Database (auto-configured)
DATABASE_URL=${db.DATABASE_URL}

# Redis (auto-configured)
REDIS_URL=${redis.REDIS_URL}

# External Services
REPLICATE_API_TOKEN=r8_your-production-token
BACKBLAZE_APPLICATION_KEY_ID=your-key-id
BACKBLAZE_APPLICATION_KEY=your-key
BACKBLAZE_BUCKET_NAME=your-bucket
CLOUDFLARE_CDN_URL=https://your-cdn.cloudflare.com
```

#### 4. Deploy
```bash
# Automatic deployment on push to main
# Or manual deployment:
doctl apps create-deployment your-app-id
```

### AWS ECS Deployment

#### 1. Build and Push Image
```bash
# Build image
docker build -t your-registry/ai-compliance-agent:latest .

# Push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin your-registry.dkr.ecr.us-west-2.amazonaws.com
docker push your-registry/ai-compliance-agent:latest
```

#### 2. Deploy with Terraform
```bash
# Initialize Terraform
cd terraform/
terraform init
terraform plan
terraform apply
```

## 🔧 Configuration Validation

### Run Configuration Validator
```bash
cd backend
python manage.py shell
>>> from compliance_app.config_validator import validate_config
>>> validate_config()
```

### Check Environment Variables
```bash
# List all environment variables
env | grep -E "(SECRET_KEY|DATABASE_URL|REDIS_URL|REPLICATE_API_TOKEN)"
```

### Test Database Connection
```bash
cd backend
python manage.py dbshell
# Should connect successfully
```

### Test Redis Connection
```bash
redis-cli -u $REDIS_URL ping
# Should return PONG
```

## 🧪 Test Data Management

### Create Test Fixtures
```bash
# Create fixtures with test data
python manage.py dumpdata users.User projects.Project --indent 2 > fixtures/test_data.json

# Load test data
python manage.py loaddata fixtures/test_data.json
```

### Factory for Test Data
```bash
# Install factory-boy
pip install factory-boy

# Use factories in tests
from tests.factories import UserFactory, ProjectFactory

user = UserFactory()
project = ProjectFactory(owner=user)
```

## 🔍 Debugging

### Enable Debug Mode
```bash
# Set in .env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Check Logs
```bash
# Django logs
tail -f logs/django.log

# Celery logs
tail -f logs/celery.log

# Application logs (DigitalOcean)
doctl apps logs your-app-id --follow
```

### Database Debugging
```bash
# Django shell
python manage.py shell

# Check database
>>> from projects.models import Project
>>> Project.objects.count()
>>> from users.models import User
>>> User.objects.all()
```

### Performance Debugging
```bash
# Enable Django Debug Toolbar
pip install django-debug-toolbar

# Add to INSTALLED_APPS and settings
# Check queries in browser
```

## 📊 Monitoring

### Health Check
```bash
# Test health endpoint
curl http://localhost:8000/health/

# Should return:
# {"status": "healthy", "database": "ok", "redis": "ok"}
```

### Monitor Celery
```bash
# Check active tasks
celery -A compliance_app inspect active

# Check worker stats
celery -A compliance_app inspect stats
```

### Database Performance
```bash
# Check slow queries
python manage.py shell
>>> from django.db import connection
>>> connection.queries
```

## 🚨 Common Issues

### Database Migration Issues
```bash
# Check migration status
python manage.py showmigrations

# Reset migrations (last resort)
python manage.py migrate app_name zero
python manage.py migrate app_name
```

### Celery Worker Issues
```bash
# Restart worker
pkill -f celery
celery -A compliance_app worker --loglevel=info

# Check Redis connection
redis-cli ping
```

### File Upload Issues
```bash
# Check file permissions
ls -la media/
chmod 755 media/

# Check storage configuration
python manage.py shell
>>> from django.core.files.storage import default_storage
>>> default_storage.exists('test')
```

### Permission Issues
```bash
# Create superuser
python manage.py createsuperuser

# Check user roles
python manage.py shell
>>> from users.models import User
>>> user = User.objects.first()
>>> user.is_admin, user.is_operator, user.is_client
```

## 📞 Getting Help

### Check Documentation
- README.md: Comprehensive guide
- TESTING_AND_DEPLOYMENT.md: Detailed testing/deployment
- CONFIGURATION.md: Configuration reference
- BUG_ANALYSIS_REPORT.md: Known issues and fixes

### Common Commands
```bash
# Validate configuration
python backend/compliance_app/config_validator.py

# Run tests
cd backend && python manage.py test

# Check migrations
python manage.py showmigrations

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### Debug Mode Checklist
- [ ] DEBUG=True in .env
- [ ] LOG_LEVEL=DEBUG
- [ ] Database connection working
- [ ] Redis connection working
- [ ] External API tokens valid
- [ ] File permissions correct

### Production Deployment Checklist
- [ ] DEBUG=False
- [ ] SECRET_KEY set and secure
- [ ] ALLOWED_HOSTS configured
- [ ] DATABASE_URL uses PostgreSQL
- [ ] REDIS_URL uses production Redis
- [ ] All external API tokens set
- [ ] Static files collected
- [ ] Database migrations run
- [ ] Health check passing
- [ ] Monitoring configured

---

This guide provides quick reference for common tasks. For detailed information, see the full documentation files.