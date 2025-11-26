"""
Django settings for compliance_app project - Development Environment.

This module contains development-specific settings.
Use this for local development with DEBUG=True.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Database
# Use SQLite for simple local development or PostgreSQL with DATABASE_URL
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'))
}

# Email Backend - Console output for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@localhost')
ADMIN_EMAIL = env('ADMIN_EMAIL', default='admin@localhost')

# Disable HTTPS redirects in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS Settings for development (if using separate frontend)
CORS_ALLOW_ALL_ORIGINS = True

# Additional development apps
INSTALLED_APPS += [
    # Uncomment for development tools
    # 'debug_toolbar',
    # 'django_extensions',
]

# Development middleware
# MIDDLEWARE += [
#     'debug_toolbar.middleware.DebugToolbarMiddleware',
# ]

# Internal IPs for debug toolbar
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Development logging - more verbose
LOGGING['root']['level'] = 'DEBUG'

# Replicate token not required in development (will use dummy value)
if not REPLICATE_API_TOKEN:
    REPLICATE_API_TOKEN = 'dummy_token_for_dev'

# Celery eager mode for development (tasks run synchronously)
# Uncomment to test without Celery/Redis running
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True
