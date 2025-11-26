# ============================================================
# AI-Compliance Agent - Multi-Stage Docker Build
# ============================================================
# This Dockerfile creates optimized production-ready images
# with proper layer caching and minimal attack surface

# ============================================================
# Stage 1: Base Image with System Dependencies
# ============================================================
FROM python:3.11.8-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg for video processing
    ffmpeg \
    # libmagic for file type detection
    libmagic1 \
    # PostgreSQL client for database operations
    libpq5 \
    # SSL certificates
    ca-certificates \
    # For entrypoint script
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security (don't run as root)
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# ============================================================
# Stage 2: Python Dependencies
# ============================================================
FROM base as dependencies

# Install build dependencies (only in this stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create directory for dependencies
WORKDIR /deps

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --prefix=/deps/python-packages

# ============================================================
# Stage 3: Final Production Image
# ============================================================
FROM base as production

# Copy installed Python packages from dependencies stage
COPY --from=dependencies /deps/python-packages /usr/local

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/backend/staticfiles /app/backend/media /tmp && \
    chown -R appuser:appuser /app /tmp

# Copy entrypoint script
COPY --chown=appuser:appuser scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Copy application code
COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser .env.example /app/.env.example

# Switch to non-root user
USER appuser

# Set environment defaults for production
ENV DJANGO_SETTINGS_MODULE=compliance_app.settings \
    DJANGO_ENV=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/login/').read()" || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command: Run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "compliance_app.wsgi:application"]
