"""
Django settings for compliance_app project - Production Environment.

This module contains production-specific settings.
All sensitive data should come from environment variables.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

# SECURITY: Allowed hosts must be set in production
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

if not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be set in production environment")

# Database - PostgreSQL required in production
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Validate that PostgreSQL is being used
if not DATABASES['default']['ENGINE'].endswith('postgresql'):
    raise ValueError("PostgreSQL is required in production. Set DATABASE_URL to postgres://...")

# Email Configuration - SMTP required in production
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
ADMIN_EMAIL = env('ADMIN_EMAIL', default='admin@localhost')

# Security Settings for Production
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=True)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CSRF Settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Session Settings
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# Validate critical environment variables
if not SECRET_KEY or SECRET_KEY == 'unsafe-secret-key':
    raise ValueError("SECRET_KEY must be set to a secure value in production")

if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN must be set in production")

if not BACKBLAZE_CONFIG['ENDPOINT_URL']:
    raise ValueError("BACKBLAZE_ENDPOINT_URL must be set in production")

if not BACKBLAZE_CONFIG['APPLICATION_KEY_ID']:
    raise ValueError("BACKBLAZE_APPLICATION_KEY_ID must be set in production")

if not BACKBLAZE_CONFIG['APPLICATION_KEY']:
    raise ValueError("BACKBLAZE_APPLICATION_KEY must be set in production")

if not BACKBLAZE_CONFIG['BUCKET_NAME']:
    raise ValueError("BACKBLAZE_BUCKET_NAME must be set in production")

# Static files handling with WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging for production - structured output
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# REST Framework - Production settings
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]

# Cache Configuration (using Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'compliance_app',
        'TIMEOUT': 300,
    }
}
