# Примеры исправлений критических проблем

## 1. Исправление валидации размера файлов

### Файл: backend/projects/forms.py

```python
from django import forms
from django.core.exceptions import ValidationError
import magic

class VideoUploadForm(forms.ModelForm):
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    ALLOWED_MIME_TYPES = [
        'video/mp4', 'video/avi', 'video/mov', 
        'video/wmv', 'video/flv', 'video/webm'
    ]
    
    class Meta:
        model = Video
        fields = ['original_name', 'video_file', 'video_url']
    
    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if not video_file:
            return video_file
            
        # Проверка размера
        if video_file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f'Размер файла не должен превышать {self.MAX_FILE_SIZE // (1024*1024)}MB'
            )
        
        # Проверка MIME типа
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(video_file.read(1024))
        video_file.seek(0)
        
        if file_type not in self.ALLOWED_MIME_TYPES:
            raise ValidationError(
                f'Неподдерживаемый формат файла: {file_type}'
            )
        
        return video_file
    
    def clean(self):
        cleaned_data = super().clean()
        video_file = cleaned_data.get('video_file')
        video_url = cleaned_data.get('video_url')
        
        if not video_file and not video_url:
            raise ValidationError('Необходимо указать либо файл, либо URL видео')
        
        if video_file and video_url:
            raise ValidationError('Нельзя указывать и файл, и URL одновременно')
        
        return cleaned_data
```

### Файл: backend/projects/views.py

```python
import cv2
from django.core.files.uploadedfile import InMemoryUploadedFile

class VideoUploadView(LoginRequiredMixin, ClientAccessMixin, CreateView):
    def form_valid(self, form):
        # Получаем длительность видео для проверки баланса
        video_file = form.cleaned_data.get('video_file')
        video_url = form.cleaned_data.get('video_url')
        
        video_duration = 0
        try:
            if video_file:
                video_duration = self._get_video_duration_from_file(video_file)
            elif video_url:
                video_duration = self._get_video_duration_from_url(video_url)
        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            messages.error(self.request, 'Не удалось определить длительность видео')
            return self.form_invalid(form)
        
        # Проверка баланса
        required_minutes = max(1, int(video_duration / 60))  # Минимум 1 минута
        if not self.request.user.has_sufficient_balance(required_minutes):
            messages.error(
                self.request, 
                f'Недостаточно минут на балансе. Требуется: {required_minutes}, доступно: {self.request.user.balance_minutes}'
            )
            return self.form_invalid(form)
        
        # Продолжаем с оригинальной логикой
        form.instance.project = self.project
        response = super().form_valid(form)
        
        # Запускаем обработку
        from ai_pipeline.tasks import process_video
        process_video.delay(str(self.object.id))
        
        messages.success(self.request, 'Видео загружено и отправлено на обработку!')
        return response
    
    def _get_video_duration_from_file(self, video_file: InMemoryUploadedFile) -> float:
        """Получить длительность видео из загруженного файла"""
        # Сохраняем временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            for chunk in video_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        try:
            cap = cv2.VideoCapture(tmp_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            return duration
        finally:
            import os
            os.unlink(tmp_path)
    
    def _get_video_duration_from_url(self, video_url: str) -> float:
        """Получить длительность видео из URL (без скачивания)"""
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('duration', 0) or 0
```

## 2. Исправление SSRF уязвимости

### Файл: backend/ai_pipeline/services/ffmpeg_service.py

```python
import re
from urllib.parse import urlparse
import ipaddress

class VideoPreprocessor:
    ALLOWED_SCHEMES = ['http', 'https']
    BLOCKED_DOMAINS = ['localhost', '127.0.0.1', '0.0.0.0', 'metadata.google.internal']
    BLOCKED_NETWORKS = [
        ipaddress.IPv4Network('127.0.0.0/8'),    # Loopback
        ipaddress.IPv4Network('10.0.0.0/8'),      # Private Class A
        ipaddress.IPv4Network('172.16.0.0/12'),   # Private Class B
        ipaddress.IPv4Network('192.168.0.0/16'), # Private Class C
        ipaddress.IPv4Network('169.254.0.0/16'), # Link-local
        ipaddress.IPv4Network('224.0.0.0/4'),     # Multicast
    ]
    
    def download_from_url(self, video_url):
        # Enhanced URL validation
        if not self._is_valid_url(video_url):
            logger.error(f"Invalid or blocked video URL: {video_url}")
            raise ValueError(f"Invalid video URL: {video_url}")
        
        import yt_dlp
        ydl_opts = {
            'outtmpl': os.path.join(tempfile.gettempdir(), 'downloaded_%(id)s.%(ext)s'),
            'format': 'best[height<=1080]',
            'quiet': True,
            'nocheckcertificate': False,  # Certificate validation
            'socket_timeout': 60,          # Timeout
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                file_path = ydl.prepare_filename(info)
                
                # Validate downloaded file
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    raise ValueError("Downloaded file is invalid or empty")
                
                logger.info(f"Video downloaded successfully: {file_path}")
                return file_path
                
        except yt_dlp.DownloadError as e:
            logger.error(f"YouTubeDL download error for URL {video_url}: {e}")
            raise ValueError(f"Failed to download video: {e}")
        except Exception as e:
            logger.error(f"Unexpected error downloading video from URL {video_url}: {e}")
            raise

    def _is_valid_url(self, url):
        try:
            result = urlparse(url)
            
            # Basic validation
            if not all([result.scheme, result.netloc]):
                return False
            
            # Scheme validation
            if result.scheme not in self.ALLOWED_SCHEMES:
                return False
            
            hostname = result.hostname
            if not hostname:
                return False
            
            # Block specific domains
            if hostname.lower() in self.BLOCKED_DOMAINS:
                return False
            
            # Block private networks
            try:
                ip = ipaddress.ip_address(hostname)
                for network in self.BLOCKED_NETWORKS:
                    if ip in network:
                        return False
            except ValueError:
                # Not an IP address, continue with domain validation
                pass
            
            # Additional domain validation
            if re.match(r'^[0-9.-]+$', hostname):  # Numeric hostname
                return False
            
            return True
            
        except (ValueError, AttributeError) as e:
            logger.error(f"URL validation error: {e}")
            return False
```

## 3. Исправление Race Condition

### Файл: backend/operators/services.py

```python
from django.db import transaction
from django.utils import timezone

class TaskQueueService:
    @classmethod
    def get_next_task(cls, operator):
        """
        Безопасное получение следующей задачи для оператора.
        Использует select_for_update для предотвращения race conditions.
        """
        with transaction.atomic():
            # Блокируем задачи для предотвращения конкурентного доступа
            task = (
                VerificationTask.objects
                .select_for_update(skip_locked=True)  # Пропускаем уже заблокированные задачи
                .filter(status=VerificationTask.Status.PENDING)
                .order_by('created_at', 'id')  # Детерминированный порядок
                .first()
            )
            
            if not task:
                return None
            
            # Назначаем задачу оператору
            task.operator = operator
            task.status = VerificationTask.Status.IN_PROGRESS
            task.started_at = timezone.now()
            task.save(update_fields=['operator', 'status', 'started_at'])
            
            logger.info(f"Task {task.id} assigned to operator {operator.id}")
            return task
    
    @classmethod
    def release_task(cls, task, reason=""):
        """
        Безопасное освобождение задачи (возвращает её в пул ожидания)
        """
        with transaction.atomic():
            task = VerificationTask.objects.select_for_update().get(id=task.id)
            
            if task.status == VerificationTask.Status.IN_PROGRESS:
                task.operator = None
                task.status = VerificationTask.Status.PENDING
                task.started_at = None
                task.save(update_fields=['operator', 'status', 'started_at'])
                
                if reason:
                    logger.info(f"Task {task.id} released back to queue. Reason: {reason}")
```

### Файл: backend/operators/tasks.py

```python
@shared_task(bind=True, max_retries=3)
def assign_pending_tasks(self, batch_size: int = 50) -> int:
    """
    Периодическая задача для назначения ожидающих задач операторам.
    Использует оптимистичную блокировку для избежания race conditions.
    """
    from users.models import User
    from operators.models import VerificationTask
    from django.db import transaction
    
    assigned_count = 0
    
    try:
        # Получаем активных операторов
        operators = User.objects.filter(
            role=UserRole.OPERATOR, 
            is_active=True,
            is_active_operator=True
        ).order_by('-performance_metric')[:batch_size]
        
        for operator in operators:
            try:
                # Получаем задачу с блокировкой
                with transaction.atomic():
                    task = (
                        VerificationTask.objects
                        .select_for_update(skip_locked=True)
                        .filter(status=VerificationTask.Status.PENDING)
                        .order_by('created_at', 'id')
                        .first()
                    )
                    
                    if task:
                        # Назначаем задачу
                        task.operator = operator
                        task.status = VerificationTask.Status.IN_PROGRESS
                        task.started_at = timezone.now()
                        task.save(update_fields=['operator', 'status', 'started_at'])
                        
                        assigned_count += 1
                        logger.info(
                            f"Task {task.id} assigned to operator {operator.id} ({operator.email})"
                        )
                        
            except Exception as exc:
                logger.exception(
                    f"Failed to assign task to operator {operator.id}: {exc}"
                )
                continue
    
    except Exception as exc:
        logger.error(f"Critical error in assign_pending_tasks: {exc}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
    
    logger.info(f"Task assignment completed. Assigned {assigned_count} tasks.")
    return assigned_count
```

## 4. Улучшенная обработка ошибок в AI сервисах

### Файл: backend/ai_pipeline/services/ai_services.py

```python
import replicate
from replicate.exceptions import ReplicateError
from typing import Dict, Any, Optional
import time
from tenacity import retry, stop_after_attempt, wait_exponential

class TranscriptionError(Exception):
    """Custom exception for transcription errors"""
    pass

class VideoAnalysisError(Exception):
    """Custom exception for video analysis errors"""
    pass

class WhisperASRService:
    def __init__(self):
        api_token = settings.REPLICATE_API_TOKEN
        if not api_token:
            raise ValueError("REPLICATE_API_TOKEN is not set in settings.")
        
        self.client = replicate.Client(
            api_token=api_token,
            timeout=getattr(settings, 'REPLICATE_API_TIMEOUT', 300)
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Транскрибация аудио с retry логикой и улучшенной обработкой ошибок
        """
        if not os.path.exists(audio_path):
            raise TranscriptionError(f"Audio file not found: {audio_path}")
        
        # Проверяем размер файла
        file_size = os.path.getsize(audio_path)
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            raise TranscriptionError(f"Audio file too large: {file_size} bytes")
        
        try:
            with open(audio_path, 'rb') as audio_file:
                # Валидация формата файла
                if not self._is_valid_audio_format(audio_file):
                    raise TranscriptionError("Invalid audio format")
                
                audio_file.seek(0)
                
                prediction = self.client.run(
                    settings.WHISPER_MODEL_ID,
                    input={
                        "audio": audio_file,
                        "model": "small",
                        "language": "ru",
                    }
                )
                
                # Валидация результата
                if not prediction or not isinstance(prediction, dict):
                    raise TranscriptionError("Invalid transcription result")
                
                return prediction
                
        except ReplicateError as e:
            logger.error(f"Replicate API error during transcription: {e}")
            raise TranscriptionError(f"AI service error: {str(e)}")
        except FileNotFoundError:
            logger.error(f"Audio file not found: {audio_path}")
            raise TranscriptionError("Audio file not found")
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    
    def _is_valid_audio_format(self, audio_file) -> bool:
        """Проверка формата аудио файла"""
        import magic
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_buffer(audio_file.read(1024))
            audio_file.seek(0)
            
            allowed_types = [
                'audio/wav', 'audio/mp3', 'audio/mpeg', 
                'audio/ogg', 'audio/flac', 'audio/x-wav'
            ]
            
            return file_type in allowed_types
        except Exception:
            return False

class VideoAnalyticsService:
    def __init__(self):
        api_token = settings.REPLICATE_API_TOKEN
        if not api_token:
            raise ValueError("REPLICATE_API_TOKEN is not set in settings.")
        
        self.client = replicate.Client(
            api_token=api_token,
            timeout=getattr(settings, 'REPLICATE_API_TIMEOUT', 300)
        )
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        reraise=True
    )
    def analyze_frame(self, frame_path: str, timestamp: int) -> Dict[str, Any]:
        """
        Анализ кадра с retry логикой
        """
        if not os.path.exists(frame_path):
            raise VideoAnalysisError(f"Frame file not found: {frame_path}")
        
        results = {
            'timestamp': timestamp,
            'yolo_objects': [],
            'nsfw_score': 0.0,
            'violence_score': 0.0,
            'ocr_text': []
        }
        
        try:
            with open(frame_path, 'rb') as frame_file:
                # Валидация изображения
                if not self._is_valid_image_format(frame_file):
                    raise VideoAnalysisError("Invalid image format")
                
                frame_file.seek(0)
                
                # YOLO objects detection
                try:
                    yolo_results = self.client.run(
                        settings.YOLO_MODEL_ID,
                        input={"image": frame_file, "confidence": 0.25}
                    )
                    results['yolo_objects'] = yolo_results or []
                except ReplicateError as e:
                    logger.warning(f"YOLO analysis failed for frame {timestamp}: {e}")
                    results['yolo_objects'] = []
                
                # NSFW detection
                frame_file.seek(0)
                try:
                    nsfw_results = self.client.run(
                        settings.NSFW_MODEL_ID,
                        input={"image": frame_file}
                    )
                    results['nsfw_score'] = nsfw_results.get('nsfw', 0.0) if nsfw_results else 0.0
                except ReplicateError as e:
                    logger.warning(f"NSFW analysis failed for frame {timestamp}: {e}")
                    results['nsfw_score'] = 0.0
            
            return results
            
        except VideoAnalysisError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during frame analysis: {e}")
            raise VideoAnalysisError(f"Frame analysis failed: {str(e)}")
    
    def _is_valid_image_format(self, image_file) -> bool:
        """Проверка формата изображения"""
        import magic
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_buffer(image_file.read(1024))
            image_file.seek(0)
            
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            return file_type in allowed_types
        except Exception:
            return False
```

## 5. Безопасное хранение конфигурации

### Файл: backend/compliance_app/settings.py

```python
import environ
from django.core.exceptions import ImproperlyConfigured

# Enhanced environment validation
def get_required_env(key: str) -> str:
    """Get required environment variable or raise error"""
    value = env(key)
    if not value:
        raise ImproperlyConfigured(f"Required environment variable {key} is not set")
    return value

def get_env_with_default(key: str, default: str, required_in_prod: bool = False) -> str:
    """Get environment variable with default, optionally required in production"""
    value = env(key, default=default)
    
    if required_in_prod and not DEBUG and value == default:
        raise ImproperlyConfigured(
            f"Environment variable {key} must be set in production (not using default)"
        )
    
    return value

# Security settings with validation
SECRET_KEY = get_required_env('SECRET_KEY')

# API tokens with validation
REPLICATE_API_TOKEN = get_required_env('REPLICATE_API_TOKEN')
REPLICATE_API_TIMEOUT = env.int('REPLICATE_API_TIMEOUT', default=300)

# Backblaze configuration with validation
BACKBLAZE_CONFIG = {
    'ENDPOINT_URL': get_env_with_default('BACKBLAZE_ENDPOINT_URL', ''),
    'APPLICATION_KEY_ID': get_required_env('BACKBLAZE_APPLICATION_KEY_ID'),
    'APPLICATION_KEY': get_required_env('BACKBLAZE_APPLICATION_KEY'),
    'BUCKET_NAME': get_required_env('BACKBLAZE_BUCKET_NAME'),
    'CLOUDFLARE_CDN_URL': get_env_with_default('CLOUDFLARE_CDN_URL', ''),
}

# Validate Backblaze config
if not all(BACKBLAZE_CONFIG.values()):
    raise ImproperlyConfigured("All Backblaze configuration variables must be set")

# Content filtering lists from environment
PROFANITY_LIST = env.list('PROFANITY_LIST', default=[])
BRAND_LIST = env.list('BRAND_LIST', default=[])

# File upload limits
MAX_VIDEO_SIZE_MB = env.int('MAX_VIDEO_SIZE_MB', default=500)
MAX_VIDEO_DURATION_MINUTES = env.int('MAX_VIDEO_DURATION_MINUTES', default=120)

# Rate limiting
RATELIMIT_ENABLE = env.bool('RATELIMIT_ENABLE', default=True)
RATELIMIT_RATE = env('RATELIMIT_RATE', default='100/h')

# Security headers
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=not DEBUG)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=True)
```

Эти примеры показывают конкретные исправления для самых критических проблем, обнаруженных в коде.
