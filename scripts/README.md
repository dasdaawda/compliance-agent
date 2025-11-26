# Scripts

This directory contains utility scripts for the AI-Compliance Agent project.

## entrypoint.sh

Docker entrypoint script that:

1. Waits for PostgreSQL database to be ready
2. Runs Django migrations (`python manage.py migrate`)
3. Collects static files (`python manage.py collectstatic`)
4. Starts the application (Gunicorn or other command)

Used in Dockerfile as the entrypoint to ensure proper initialization order.

### Usage

In Dockerfile:
```dockerfile
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "compliance_app.wsgi:application"]
```

In docker-compose.yml:
```yaml
command: gunicorn --bind 0.0.0.0:8000 compliance_app.wsgi:application
# entrypoint.sh is automatically used from Dockerfile
```
