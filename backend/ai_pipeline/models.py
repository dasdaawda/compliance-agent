import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
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
    
    risk_code = models.ForeignKey(
        'RiskDefinition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggers',
        verbose_name=_('код риска')
    )
    raw_payload = models.JSONField(
        _('сырые данные'),
        null=True,
        blank=True,
        help_text=_('Полный ответ API для аудита')
    )
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Ожидает проверки')
        PROCESSED = 'processed', _('Обработан оператором')
    
    status = models.CharField(_('статус'), max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('AI триггер')
        verbose_name_plural = _('AI триггеры')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video', 'status']),
            models.Index(fields=['status']),
        ]

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
    
    last_step = models.CharField(_('последний выполненный шаг'), max_length=100, blank=True)
    retry_count = models.IntegerField(_('количество повторов'), default=0)
    error_trace = models.JSONField(_('трасса ошибок'), default=list, blank=True)
    
    started_at = models.DateTimeField(_('время начала'), null=True, blank=True)
    completed_at = models.DateTimeField(_('время завершения'), null=True, blank=True)
    processing_time_seconds = models.IntegerField(_('время обработки (сек)'), default=0)
    api_calls_count = models.IntegerField(_('количество вызовов API'), default=0)
    cost_estimate = models.DecimalField(_('оценка стоимости'), max_digits=10, decimal_places=6, default=Decimal('0.0'))

    class Meta:
        verbose_name = _('выполнение пайплайна')
        verbose_name_plural = _('выполнения пайплайнов')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        video_name = self.video.original_name if self.video else "Unknown Video"
        return f"Pipeline for {video_name}"


class RiskDefinition(models.Model):
    """Определение риска/триггера для справочной информации."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(_('код риска'), max_length=50, unique=True, db_index=True, default=uuid.uuid4, help_text=_('Код из таблицы рисков'))
    trigger_source = models.CharField(_('источник триггера'), max_length=50, choices=AITrigger.TriggerSource.choices)
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
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['trigger_source']),
        ]

    def __str__(self):
        return f"{self.name} [{self.code}]"


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
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_tasks',
        verbose_name=_('заблокировано'),
        help_text=_('Оператор, который заблокировал задачу')
    )
    status = models.CharField(_('статус'), max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    priority = models.IntegerField(_('приоритет'), default=0, help_text=_('Приоритет задачи (выше = важнее)'))
    
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    started_at = models.DateTimeField(_('время начала'), null=True, blank=True)
    locked_at = models.DateTimeField(_('время блокировки'), null=True, blank=True)
    completed_at = models.DateTimeField(_('время завершения'), null=True, blank=True)
    total_processing_time = models.IntegerField(_('общее время обработки (сек)'), default=0)
    
    # Task locking fields
    expires_at = models.DateTimeField(_('истекает в'), null=True, blank=True, help_text=_('Время, когда блокировка задачи истекает'))
    last_heartbeat = models.DateTimeField(_('последний heartbeat'), null=True, blank=True, help_text=_('Последнее обновление активности оператора'))
    decision_summary = models.TextField(_('суммарное решение'), blank=True, help_text=_('Итоговое описание принятых решений'))

    class Meta:
        verbose_name = _('задача на верификацию')
        verbose_name_plural = _('задачи на верификацию')
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['operator', 'status']),
        ]

    def __str__(self):
        video_name = self.video.original_name if self.video else "Unknown Video"
        return f"Verification: {video_name}"
    
    def assign_to_operator(self, user):
        """Назначить задачу оператору с блокировкой"""
        from django.db import transaction
        from django.utils import timezone
        from datetime import timedelta
        
        with transaction.atomic():
            # Проверяем, что задача все еще доступна для назначения
            current_task = VerificationTask.objects.select_for_update().get(id=self.id)
            if current_task.status != self.Status.PENDING:
                raise ValueError(f"Task {self.id} is not pending (current: {current_task.status})")
            
            self.operator = user
            self.locked_by = user
            self.status = self.Status.IN_PROGRESS
            self.started_at = timezone.now()
            self.locked_at = timezone.now()
            self.expires_at = timezone.now() + timedelta(hours=2)  # 2 часа блокировка
            self.last_heartbeat = timezone.now()
            self.save(update_fields=['operator', 'locked_by', 'status', 'started_at', 'locked_at', 'expires_at', 'last_heartbeat'])
    
    def heartbeat(self):
        """Обновить время активности и продлить блокировку"""
        from django.utils import timezone
        from datetime import timedelta
        
        if self.operator is None or self.status != self.Status.IN_PROGRESS:
            raise ValueError("Cannot heartbeat on unassigned or non-in-progress task")
        
        self.last_heartbeat = timezone.now()
        self.expires_at = timezone.now() + timedelta(hours=1)  # Продлеваем на 1 час
        self.save(update_fields=['last_heartbeat', 'expires_at'])
    
    def complete(self, decision_summary=""):
        """Завершить задачу с решением"""
        from django.utils import timezone
        
        if self.operator is None or self.status != self.Status.IN_PROGRESS:
            raise ValueError("Cannot complete unassigned or non-in-progress task")
        
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.decision_summary = decision_summary
        self.expires_at = None
        self.locked_at = None
        self.locked_by = None
        self.last_heartbeat = None
        if self.started_at:
            self.total_processing_time = int((self.completed_at - self.started_at).total_seconds())
        self.save(update_fields=[
            'status', 'completed_at', 'decision_summary', 'total_processing_time',
            'expires_at', 'locked_at', 'locked_by', 'last_heartbeat'
        ])
    
    def complete_task(self, decision_summary=""):
        """Alias for complete() to avoid missing method errors"""
        return self.complete(decision_summary=decision_summary)
    
    def release_lock(self):
        """Освободить блокировку задачи (возвращает в PENDING)"""
        from django.db import transaction
        from django.utils import timezone
        
        with transaction.atomic():
            current_task = VerificationTask.objects.select_for_update().get(id=self.id)
            if current_task.status == self.Status.IN_PROGRESS:
                current_task.status = self.Status.PENDING
                current_task.operator = None
                current_task.locked_by = None
                current_task.locked_at = None
                current_task.expires_at = None
                current_task.last_heartbeat = None
                current_task.save(update_fields=['status', 'operator', 'locked_by', 'locked_at', 'expires_at', 'last_heartbeat'])
    
    def release(self):
        """Alias for release_lock() for backward compatibility"""
        return self.release_lock()
    
    def is_locked(self):
        """Проверить, заблокирована ли задача и не истекло ли время"""
        from django.utils import timezone
        
        if self.status != self.Status.IN_PROGRESS or self.expires_at is None:
            return False
        return timezone.now() < self.expires_at
    
    def is_stale(self):
        """Проверить, устарела ли блокировка задачи"""
        from django.utils import timezone
        
        if self.status != self.Status.IN_PROGRESS or self.expires_at is None:
            return False
        return timezone.now() > self.expires_at
