# 📋 Deployment Checklist

Use this checklist to ensure proper deployment of AI-Compliance Agent.

## Pre-Deployment

### 1. Environment Setup

- [ ] Python 3.11.8 installed (check `runtime.txt`)
- [ ] All environment variables set in `.env` (see `.env.example`)
- [ ] `DJANGO_ENV=production` set
- [ ] `SECRET_KEY` is unique and secure (not default)
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` includes your domain

### 2. External Services

- [ ] PostgreSQL database created
- [ ] Redis instance ready
- [ ] Backblaze B2 bucket created and configured
- [ ] Replicate API token obtained
- [ ] Email service configured (SMTP)
- [ ] Cloudflare CDN configured (optional but recommended)

### 3. Configuration Validation

```bash
# Run config validator
python backend/compliance_app/config_validator.py

# Should output: ✅ Конфигурация валидна!
```

### 4. Dependencies

```bash
# Install pinned dependencies
pip install -r requirements.txt

# Verify installation
pip freeze | grep Django
# Should show: Django==5.0.6
```

## Deployment Steps

### 5. Database Migrations

```bash
cd backend
python manage.py migrate --noinput
```

### 6. Static Files

```bash
python manage.py collectstatic --noinput
```

### 7. Django Check

```bash
# Run deployment checks
python manage.py check --deploy --settings compliance_app.settings

# Should pass all checks
```

### 8. Create Superuser

```bash
python manage.py createsuperuser
```

## Docker Deployment

### 9. Docker Build

```bash
# Build the image
docker build -t ai-compliance-agent:latest .

# Or with docker-compose
docker compose build
```

### 10. Docker Compose

```bash
# Start all services
docker compose up -d

# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser
```

## Post-Deployment

### 11. Service Health Checks

- [ ] Web service responds: `curl http://localhost:8000/admin/login/`
- [ ] Database connection works: `python manage.py dbshell`
- [ ] Celery worker running: Check logs for "celery@hostname ready"
- [ ] Redis connection works: `redis-cli ping`

### 12. Functional Tests

- [ ] Admin login works at `/admin/`
- [ ] API documentation accessible at `/api/docs/`
- [ ] Video upload works (test with small video)
- [ ] Celery task processing works
- [ ] Email notifications send correctly

### 13. Security Checks

- [ ] HTTPS redirect enabled (`SECURE_SSL_REDIRECT=True`)
- [ ] HSTS headers set (`SECURE_HSTS_SECONDS=31536000`)
- [ ] Session cookies secure (`SESSION_COOKIE_SECURE=True`)
- [ ] CSRF cookies secure (`CSRF_COOKIE_SECURE=True`)
- [ ] No DEBUG information exposed
- [ ] Error pages don't leak sensitive data

### 14. Monitoring Setup

- [ ] Application logs accessible
- [ ] Celery worker logs accessible
- [ ] Database metrics monitored
- [ ] Replicate API usage tracking
- [ ] B2 storage usage tracking
- [ ] Error tracking configured (Sentry optional)

### 15. Backup Strategy

- [ ] Database backup scheduled
- [ ] B2 lifecycle rules configured
- [ ] Configuration backed up securely

## Common Issues

### Settings Module Error

```bash
# Error: No module named 'compliance_app.settings'
# Solution: Check DJANGO_SETTINGS_MODULE environment variable
export DJANGO_SETTINGS_MODULE=compliance_app.settings
export DJANGO_ENV=production
```

### Database Connection Error

```bash
# Error: could not connect to server
# Solution: Check DATABASE_URL format
# Correct: postgres://user:pass@host:5432/dbname
# With SSL: postgres://user:pass@host:5432/dbname?sslmode=require
```

### Static Files Not Found

```bash
# Solution: Run collectstatic
python manage.py collectstatic --noinput

# In Docker: Entrypoint script handles this automatically
```

### Celery Not Processing Tasks

```bash
# Check Celery connection
celery -A compliance_app inspect ping

# Check Redis connection
redis-cli -u $REDIS_URL ping

# Restart worker
docker compose restart celery-worker
```

## Rollback Plan

If deployment fails:

1. **Database**: Restore from backup if migrations failed
2. **Code**: Revert to previous Git commit
3. **Environment**: Restore previous `.env` configuration
4. **Services**: Restart all services with previous version

```bash
# Quick rollback with Docker
docker compose down
git checkout main  # or previous stable branch
docker compose up -d --build
```

## Performance Optimization

Post-deployment optimizations:

- [ ] Enable Redis caching
- [ ] Configure CDN for static files
- [ ] Set up database connection pooling
- [ ] Configure Celery autoscaling
- [ ] Enable Gunicorn worker optimization
- [ ] Set up query optimization (pg_stat_statements)

## Maintenance Tasks

Regular maintenance:

- [ ] Update dependencies monthly (test in staging first)
- [ ] Review and rotate secrets quarterly
- [ ] Clean up old artifacts (Celery beat job handles this)
- [ ] Monitor and optimize database queries
- [ ] Review Replicate API costs
- [ ] Check B2 storage costs

---

**Note**: This checklist should be reviewed and updated as the project evolves.
