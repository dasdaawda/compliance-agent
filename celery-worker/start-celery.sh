#!/bin/bash
cd /app/backend
celery -A compliance_app worker --loglevel=info --concurrency=2