# 🏗️ Рекомендации по улучшению архитектуры

## Общие рекомендации для долгосрочного развития

---

## 📋 1. Архитектурные улучшения

### 1.1. Микросервисная архитектура
**Текущая проблема:** Монолитная структура Django приложения затрудняет масштабирование

**Рекомендация:**
```
ai-compliance-agent/
├── api-gateway/           # Nginx/Traefik для роутинга
├── user-service/         # Управление пользователями
├── video-service/         # Загрузка и хранение видео
├── ai-service/           # AI обработка (отдельный сервис)
├── operator-service/     # Рабочее место операторов
├── notification-service/ # Уведомления (email, push)
└── analytics-service/    # Аналитика и отчеты
```

### 1.2. Event-driven архитектура
**Рекомендация:** Внедрить RabbitMQ/Kafka для асинхронной коммуникации

```python
# Пример event-driven архитектуры
class VideoUploadedEvent:
    def __init__(self, video_id, user_id, file_size):
        self.video_id = video_id
        self.user_id = user_id
        self.file_size = file_size
        self.timestamp = timezone.now()

# Event handlers
@event_handler(VideoUploadedEvent)
def start_ai_processing(event):
    ai_service.process_video_async(event.video_id)

@event_handler(VideoUploadedEvent)
def update_user_balance(event):
    billing_service.reserve_minutes(event.user_id, event.file_size)
```

---

## 🔒 2. Улучшения безопасности

### 2.1. Аутентификация и авторизация
**Рекомендация:** Внедрить JWT + OAuth2

```python
# settings.py
REST_USE_JWT = True
JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': timedelta(hours=24),
    'JWT_REFRESH_EXPIRATION_DELTA': timedelta(days=7),
    'JWT_AUTH_HEADER_PREFIX': 'Bearer',
}

# permissions.py
class VideoPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        return obj.owner == request.user
```

### 2.2. Rate Limiting и Throttling
**Рекомендация:** Django REST Framework throttling

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/hour',
        'anon': '100/hour',
        'upload': '10/hour',
        'ai_processing': '50/hour',
    }
}
```

### 2.3. Валидация и санитизация
**Рекомендация:** Pydantic для валидации данных

```python
from pydantic import BaseModel, validator
from typing import Optional

class VideoUploadRequest(BaseModel):
    title: str
    description: Optional[str] = None
    file_size: int
    
    @validator('title')
    def validate_title(cls, v):
        if len(v) < 3 or len(v) > 200:
            raise ValueError('Title must be between 3 and 200 characters')
        return v
    
    @validator('file_size')
    def validate_file_size(cls, v):
        max_size = 500 * 1024 * 1024  # 500MB
        if v > max_size:
            raise ValueError(f'File size cannot exceed {max_size} bytes')
        return v
```

---

## 🚀 3. Улучшения производительности

### 3.1. Кэширование
**Рекомендация:** Redis для многоуровневого кэширования

```python
# cache.py
from django.core.cache import caches
from django.views.decorators.cache import cache_page

# L1: In-memory cache (application level)
@cache_page(60 * 15)  # 15 minutes
def project_list(request):
    return render(request, 'projects/list.html')

# L2: Redis cache (distributed)
def get_user_projects(user_id):
    cache_key = f"user_projects:{user_id}"
    projects = caches['redis'].get(cache_key)
    
    if not projects:
        projects = Project.objects.filter(owner_id=user_id)
        caches['redis'].set(cache_key, projects, timeout=60 * 30)  # 30 minutes
    
    return projects
```

### 3.2. Оптимизация базы данных
**Рекомендация:** Индексы и query optimization

```python
# models.py - добавление индексов
class Video(models.Model):
    # ... поля ...
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['owner', 'created_at']),
        ]

# Query optimization
def get_user_videos_with_stats(user):
    return Video.objects.filter(
        project__owner=user
    ).select_related(
        'project'
    ).prefetch_related(
        'ai_triggers',
        'operator_labels'
    ).annotate(
        trigger_count=models.Count('ai_triggers'),
        label_count=models.Count('operator_labels')
    )
```

### 3.3. Асинхронная обработка
**Рекомендация:** Django Channels + WebSocket

```python
# consumers.py
class VideoProcessingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.video_id = self.scope['url_route']['kwargs']['video_id']
        self.group_name = f"video_{self.video_id}"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def video_progress(self, event):
        await self.send(text_data=json.dumps({
            'type': 'progress',
            'progress': event['progress'],
            'stage': event['stage']
        }))
```

---

## 📊 4. Мониторинг и логирование

### 4.1. Структурированное логирование
**Рекомендация:** Structured logging with JSON

```python
# logging_config.py
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
}

# usage.py
import structlog
logger = structlog.get_logger()

def process_video(video_id):
    logger.info("Starting video processing", video_id=video_id)
    try:
        # ... processing ...
        logger.info("Video processing completed", 
                   video_id=video_id, 
                   duration=processing_time)
    except Exception as e:
        logger.error("Video processing failed", 
                    video_id=video_id, 
                    error=str(e),
                    exc_info=True)
```

### 4.2. Метрики и мониторинг
**Рекомендация:** Prometheus + Grafana

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
videos_processed = Counter('videos_processed_total', 'Total videos processed')
processing_duration = Histogram('video_processing_seconds', 'Video processing time')
active_tasks = Gauge('active_processing_tasks', 'Number of active processing tasks')

# Usage in code
@processing_duration.time()
def process_video(video_id):
    active_tasks.inc()
    try:
        # ... processing ...
        videos_processed.inc()
    finally:
        active_tasks.dec()
```

---

## 🧪 5. Тестирование

### 5.1. Unit тесты
**Рекомендация:** pytest + factory_boy

```python
# test_factories.py
import factory
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.LazyAttribute(lambda obj: obj.email)
    role = UserRole.CLIENT

class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project
    
    name = factory.Faker('sentence', nb_words=3)
    owner = factory.SubFactory(UserFactory)

# test_services.py
class TestVideoProcessing:
    def test_video_transcription_success(self, mock_replicate):
        # Arrange
        service = WhisperASRService()
        audio_path = "/tmp/test_audio.wav"
        
        # Act
        result = service.transcribe(audio_path)
        
        # Assert
        assert 'segments' in result
        assert isinstance(result['segments'], list)
```

### 5.2. Integration тесты
**Рекомендация:** Testcontainers для реальных зависимостей

```python
# test_integration.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:13") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:6") as redis:
        yield redis

class TestVideoProcessingPipeline:
    def test_full_pipeline(self, client, test_video_file):
        # Upload video
        response = client.post('/api/videos/', {
            'video_file': test_video_file,
            'project': self.project.id
        })
        
        video_id = response.data['id']
        
        # Wait for processing (mocked in tests)
        process_video.delay(video_id)
        
        # Check result
        response = client.get(f'/api/videos/{video_id}/')
        assert response.data['status'] == 'completed'
```

---

## 🔄 6. CI/CD улучшения

### 6.1. GitHub Actions workflow
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml
    
    - name: Security scan
      run: |
        bandit -r . -f json -o bandit-report.json
        safety check --json --output safety-report.json
    
    - name: Code quality
      run: |
        flake8 . --format=json --output-file=flake8-report.json
        black --check .
        isort --check-only .
```

### 6.2. Docker улучшения
```dockerfile
# Multi-stage build
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM base as production
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
COPY --chown=app:app . .
USER app

# Collect static files
RUN python manage.py collectstatic --noinput

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "compliance_app.wsgi:application"]
```

---

## 📈 7. Масштабирование

### 7.1. Горизонтальное масштабирование
**Рекомендация:** Kubernetes deployment

```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-compliance-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-compliance-api
  template:
    metadata:
      labels:
        app: ai-compliance-api
    spec:
      containers:
      - name: api
        image: ai-compliance:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### 7.2. Database scaling
**Рекомендация:** Read replicas + connection pooling

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'compliance_db',
        'HOST': 'postgres-primary',
        'USER': 'app_user',
        'PASSWORD': env('DB_PASSWORD'),
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        }
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'compliance_db',
        'HOST': 'postgres-replica',
        'USER': 'readonly_user',
        'PASSWORD': env('DB_READONLY_PASSWORD'),
        'OPTIONS': {
            'MAX_CONNS': 10,
            'MIN_CONNS': 2,
        }
    }
}

DATABASE_ROUTERS = ['routers.PrimaryReplicaRouter']

# routers.py
class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label in ['projects', 'ai_pipeline']:
            return 'replica'
        return 'default'
    
    def db_for_write(self, model, **hints):
        return 'default'
```

---

## 🎯 Заключение

Эти архитектурные улучшения помогут:

1. **Масштабировать** систему под растущую нагрузку
2. **Повысить безопасность** и надежность
3. **Улучшить производительность** и пользовательский опыт
4. **Упростить поддержку** и развитие кода
5. **Обеспечить надежность** через мониторинг и тестирование

Рекомендуется внедрять изменения постепенно, начиная с самых критических улучшений безопасности и производительности.
