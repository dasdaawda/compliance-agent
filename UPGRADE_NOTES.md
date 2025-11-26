# 🔄 Upgrade Notes - Project Hardening

This document provides upgrade instructions for existing deployments.

## What Changed?

The project has been hardened with:
1. **Pinned dependencies** for reproducible builds
2. **Modular Django settings** (dev/prod separation)
3. **Multi-stage Dockerfile** for optimized images
4. **Docker Compose** for local development
5. **Comprehensive documentation** and tooling

## For Existing Deployments

### Step 1: Update Environment Variables

Add to your `.env`:
```bash
DJANGO_ENV=production
```

This tells Django to load production settings from `settings/prod.py`.

### Step 2: No Code Changes Required

The settings module path remains the same:
```python
DJANGO_SETTINGS_MODULE=compliance_app.settings
```

Your existing code, including:
- Django apps
- Models
- Views
- Celery tasks
- Management commands

...all work without modification.

### Step 3: Update Dependencies (Optional but Recommended)

```bash
pip install -r requirements.txt --upgrade
```

All dependencies now have pinned versions for consistency.

### Step 4: Rebuild Docker Images (If Using Docker)

```bash
docker compose build --no-cache
docker compose up -d
```

### Step 5: Run Migrations (If Any)

```bash
python manage.py migrate
# Or with Docker:
docker compose exec web python manage.py migrate
```

## For New Developers

### Quick Start with Docker

```bash
# Clone repository
git clone <repo-url>
cd ai-compliance-agent

# Create environment file
cp .env.docker .env

# Start services
docker compose up -d

# Initialize
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Access at http://localhost:8000
```

### Local Development (Without Docker)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements.dev.txt

# Set environment
export DJANGO_ENV=development

# Run migrations
cd backend
python manage.py migrate

# Start server
python manage.py runserver
```

## Breaking Changes

None! All changes are backward compatible.

## New Features

### 1. Environment Selection

```bash
# Development (DEBUG=True, SQLite, console email)
export DJANGO_ENV=development

# Production (DEBUG=False, PostgreSQL, SMTP, security headers)
export DJANGO_ENV=production
```

### 2. Makefile Commands

```bash
make help              # Show all commands
make docker-up         # Start Docker services
make docker-migrate    # Run migrations in Docker
make test              # Run tests
make lint              # Check code quality
```

### 3. Validation Scripts

```bash
# Validate setup
./validate_setup.sh

# Test settings import
python test_settings_import.py
```

## Troubleshooting

### "No module named 'compliance_app.settings.dev'"

**Solution:** Set `DJANGO_ENV`:
```bash
export DJANGO_ENV=production
```

### "ALLOWED_HOSTS validation error"

**Solution:** In production, set `ALLOWED_HOSTS` in `.env`:
```bash
ALLOWED_HOSTS=yourdomain.com,app.yourdomain.com
```

### "Database settings not found"

**Solution:** Ensure `DATABASE_URL` is set:
```bash
DATABASE_URL=postgres://user:pass@host:5432/dbname
```

### Docker services won't start

**Solution:** Check ports and restart:
```bash
docker compose down -v
docker compose up -d --build
```

## Rollback (If Needed)

If you need to rollback:

```bash
# Restore old settings
cd backend/compliance_app
mv settings.old.py settings.py
rm -rf settings/

# Remove DJANGO_ENV from .env
sed -i '/DJANGO_ENV/d' .env

# Restart services
# For Docker:
docker compose restart web
# For systemd:
sudo systemctl restart myapp
```

## Support

- 📖 See [README.md](README.md) for general documentation
- 🚀 See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment guide
- ⚙️ See [CONFIGURATION.md](CONFIGURATION.md) for settings
- 🐳 See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for Docker
- ✅ See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for checklist

## Testing the Upgrade

After upgrading, verify:

```bash
# Check Django
python manage.py check --deploy

# Validate config
python backend/compliance_app/config_validator.py

# Run tests
python manage.py test

# Verify setup
./validate_setup.sh
```

All should pass without errors.

---

**Questions?** Review [HARDENING_SUMMARY.md](HARDENING_SUMMARY.md) for detailed changes.
