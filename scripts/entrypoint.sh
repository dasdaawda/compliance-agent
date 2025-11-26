#!/bin/bash
set -e

# AI-Compliance Agent - Docker Entrypoint Script
# This script runs database migrations, collects static files, and starts the application

echo "========================================"
echo "AI-Compliance Agent - Starting Services"
echo "========================================"

# Change to backend directory
cd /app/backend

# Wait for database to be ready
echo "Waiting for database to be ready..."
python << END
import sys
import time
import os
import psycopg2
from urllib.parse import urlparse

max_retries = 30
retry_interval = 2

database_url = os.environ.get('DATABASE_URL', '')

if not database_url:
    print("WARNING: DATABASE_URL not set, skipping database check")
    sys.exit(0)

if database_url.startswith('sqlite'):
    print("Using SQLite, skipping database check")
    sys.exit(0)

# Parse PostgreSQL URL
result = urlparse(database_url)
username = result.username
password = result.password
database = result.path[1:]
hostname = result.hostname
port = result.port or 5432

for i in range(max_retries):
    try:
        conn = psycopg2.connect(
            dbname=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        conn.close()
        print(f"Successfully connected to database at {hostname}:{port}")
        sys.exit(0)
    except psycopg2.OperationalError as e:
        print(f"Database not ready yet (attempt {i+1}/{max_retries}): {e}")
        time.sleep(retry_interval)

print("ERROR: Could not connect to database after maximum retries")
sys.exit(1)
END

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create cache table if using database cache
# Uncomment if you use database caching
# echo "Creating cache table..."
# python manage.py createcachetable || true

echo "========================================"
echo "Setup complete! Starting application..."
echo "========================================"

# Execute the main command (from CMD in Dockerfile or docker-compose)
exec "$@"
