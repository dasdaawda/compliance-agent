"""
Django settings for compliance_app project - Base Configuration.

This module contains shared settings for all environments.
Environment-specific settings are in dev.py and prod.py.
"""

import os
import environ
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR.parent, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='unsafe-secret-key')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',
    
    'users',
    'projects',
    'ai_pipeline',
    'operators',
    'admins',
    'storage',
    
    'django_htmx',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'compliance_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'compliance_app.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Celery Configuration
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Moscow'
CELERY_TASK_ROUTES = {
    'ai_pipeline.tasks.*': {'queue': 'ai_pipeline'},
    'ai_pipeline.celery_tasks.*': {'queue': 'ai_pipeline'},
    'projects.tasks.*': {'queue': 'projects'},
    'operators.tasks.*': {'queue': 'operators'},
}
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = env.int('CELERY_WORKER_MAX_TASKS_PER_CHILD', default=100)

# Backblaze B2 Configuration
BACKBLAZE_CONFIG = {
    'ENDPOINT_URL': env('BACKBLAZE_ENDPOINT_URL', default=''),
    'APPLICATION_KEY_ID': env('BACKBLAZE_APPLICATION_KEY_ID', default=''),
    'APPLICATION_KEY': env('BACKBLAZE_APPLICATION_KEY', default=''),
    'BUCKET_NAME': env('BACKBLAZE_BUCKET_NAME', default=''),
    'CLOUDFLARE_CDN_URL': env('CLOUDFLARE_CDN_URL', default=''),
}

# B2 Retry settings
B2_MAX_RETRIES = env.int('B2_MAX_RETRIES', default=3)
B2_RETRY_BACKOFF = env.int('B2_RETRY_BACKOFF', default=2)
B2_RETRY_BACKOFF_MAX = env.int('B2_RETRY_BACKOFF_MAX', default=60)

# Replicate AI Services
REPLICATE_API_TOKEN = env('REPLICATE_API_TOKEN', default='')

# AI Model IDs (Replicate)
WHISPER_MODEL_ID = env(
    'WHISPER_MODEL_ID', 
    default="openai/whisper:4d50797290df275329f202e48c76360b3f22b08d28c196cbc54600319435f8d2"
)
YOLO_MODEL_ID = env(
    'YOLO_MODEL_ID', 
    default="adirik/yolov8:fcb0173c3d6ef4e4e73ced22d0c6c3c7d0e5d3e5b5e5e5e5e5e5e5e5e5e5e5"
)
NSFW_MODEL_ID = env(
    'NSFW_MODEL_ID', 
    default="lucataco/nsfw-image-detection:02f0b7ae9c4c3d7e4e7d5f0e5c5d5e5f5e5e5e5e5e5e5e5e5e5e5e5e5e"
)
VIOLENCE_MODEL_ID = env(
    'VIOLENCE_MODEL_ID',
    default="lucataco/vit-violence-detection:01f0b7ae9c4c3d7e4e7d5f0e5c5d5e5f5e5e5e5e5e5e5e5e5e5e5e5e5e"
)
OCR_MODEL_ID = env(
    'OCR_MODEL_ID',
    default="abiruyt/text-extract-ocr:3e6e3e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e"
)

# Replicate settings
REPLICATE_TIMEOUT = env.int('REPLICATE_TIMEOUT', default=300)

# Cloudflare (additional settings)
CLOUDFLARE_API_TOKEN = env('CLOUDFLARE_API_TOKEN', default='')
CLOUDFLARE_ZONE_ID = env('CLOUDFLARE_ZONE_ID', default='')

# AI Pipeline Settings
MAX_VIDEO_FILE_SIZE = env.int('MAX_VIDEO_FILE_SIZE', default=2147483648)  # 2GB
MAX_VIDEO_DURATION = env.int('MAX_VIDEO_DURATION', default=7200)  # 2 hours
FRAME_EXTRACTION_FPS = env.int('FRAME_EXTRACTION_FPS', default=1)
ALLOWED_VIDEO_FORMATS = env.list('ALLOWED_VIDEO_FORMATS', default=['mp4', 'avi', 'mov', 'mkv', 'webm'])
DASHBOARD_URL = env('DASHBOARD_URL', default='https://app.example.com')

# NLP Dictionaries (optional)
PROFANITY_DICT_PATH = env('PROFANITY_DICT_PATH', default='')
BRAND_DICT_PATH = env('BRAND_DICT_PATH', default='')
STOPWORDS_DICT_PATH = env('STOPWORDS_DICT_PATH', default='')

# Temporary Directory
TEMP_DIR = env('TEMP_DIR', default='/tmp')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
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
        'level': 'INFO',
    },
}

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Simple JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# DRF Spectacular (API Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'AI Compliance Agent API',
    'DESCRIPTION': 'REST API for AI video compliance checking',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}
