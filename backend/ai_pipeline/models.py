import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from projects.models import Video
from users.models import UserRole


class AITrigger(models.Model):
    class TriggerSource(models.TextChoices):
        WHISPER_PROFANITY = 'whisper_profanity', _('Whisper - Мат')
        WHISPER_BRAND = 'whisper_brand', _('Whisper - Бренд')
        FALCONSAI_NSFW = 'falconsai_nsfw', _('Falconsai - NSFW')
        VIOLENCE_DETECTOR = 'violence_detector', _('Детектор насилия')
        YOLO_OBJECT = 'yolo_object', _('YOLO - Объект')
        EASYOCR_TEXT = 'easyocr_text', _('EasyOCR - Текст')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='ai_triggers', verbose_name=_('видео'))
    timestamp_sec = models.DecimalField(_('временная метка (сек)'), max_digits=10, decimal_places=3)
    trigger_source = models.CharField(_('источник триггера'), max_length=50, choices=TriggerSource.choices)
    confidence = models.DecimalField(_('уверенность'), max_digits=5, decimal_places=2, default=Decimal('0.0'))
    data = models.JSONField(_('данные'))
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Ожидает проверки')
        PROCESSED = 'processed', _('Обработан оператором')
    
    status = models.CharField(_('статус'), max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('AI триггер')
        verbose_name_plural = _('AI триггеры')
        ordering = ['-created_at']

    def __str__(self):
        video_name = self.video.original_name if self.video else "Unknown Video"
        return f"{self.get_trigger_source_display()} @ {self.timestamp_sec}s ({video_name})"


class PipelineExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('В ожидании')
        RUNNING = 'running', _('Выполняется')
        COMPLETED = 'completed', _('Завершено')
        FAILED = 'failed', _('Ошибка')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='pipeline_execution', verbose_name=_('видео'))
    status = models.CharField(_('статус'), max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    current_task = models.CharField(_('текущая задача'), max_length=100, blank=True)
    progress = models.IntegerField(_('прогресс'), default=0)
    error_message = models.TextField(_('сообщение об ошибке'), blank=True)
    
    started_at = models.DateTimeField(_('время начала'), null=True, blank=True)
    completed_at = models.DateTimeField(_('время завершения'), null=True, blank=True)
    processing_time_seconds = models.IntegerField(_('время обработки (сек)'), default=0)
    api_calls_count = models.IntegerField(_('количество вызовов API'), default=0)
    cost_estimate = models.DecimalField(_('оценка стоимости'), max_digits=10, decimal_places=6, default=Decimal('0.0'))

    class Meta:
        verbose_name = _('выполнение пайплайна')
        verbose_name_plural = _('выполнения пайплайнов')
        ordering = ['-started_at']

    def __str__(self):
        video_name = self.video.original_name if self.video else "Unknown Video"
        return f"Pipeline for {video_name}"


class RiskDefinition(models.Model):
    """Определение риска/триггера для справочной информации."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trigger_source = models.CharField(_('источник триггера'), max_length=50, choices=AITrigger.TriggerSource.choices, unique=True)
    name = models.CharField(_('название риска'), max_length=255)
    description = models.TextField(_('описание'))
    risk_level = models.CharField(
        _('уровень риска'),
        max_length=20,
        choices=[
            ('low', _('Низкий')),
            ('medium', _('Средний')),
            ('high', _('Высокий')),
        ],
        default='medium'
    )
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('определение риска')
        verbose_name_plural = _('определения рисков')
        ordering = ['trigger_source']

    def __str__(self):
        return f"{self.name} ({self.get_trigger_source_display()})"


class VerificationTask(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('В ожидании')
        IN_PROGRESS = 'in_progress', _('В работе')
        COMPLETED = 'completed', _('Завершено')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='verification_task', verbose_name=_('видео'))
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name=_('оператор'),
        limit_choices_to={'role': UserRole.OPERATOR}
    )
    status = models.CharField(_('статус'), max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    
    started_at = models.DateTimeField(_('время начала'), null=True, blank=True)
    completed_at = models.DateTimeField(_('время завершения'), null=True, blank=True)
    total_processing_time = models.IntegerField(_('общее время обработки (сек)'), default=0)

    class Meta:
        verbose_name = _('задача на верификацию')
        verbose_name_plural = _('задачи на верификацию')
        ordering = ['-id']

    def __str__(self):
        video_name = self.video.original_name if self.video else "Unknown Video"
        return f"Verification: {video_name}"
