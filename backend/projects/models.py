import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

def get_video_upload_path(instance, filename):
    """Генерирует уникальный путь для загрузки видео."""
    ext = filename.split('.')[-1]
    return f"videos/raw/{instance.project.id}/{uuid.uuid4()}.{ext}"

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('название'), max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name=_('владелец')
    )
    description = models.TextField(_('описание'), blank=True)
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('проект')
        verbose_name_plural = _('проекты')
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_owner_project_name')
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.name or str(self.id)

class VideoStatus(models.TextChoices):
    UPLOADED = 'UPLOADED', _('Загружено')
    PROCESSING = 'PROCESSING', _('Обработка AI')
    VERIFICATION = 'VERIFICATION', _('На верификации')
    COMPLETED = 'COMPLETED', _('Готово')
    FAILED = 'FAILED', _('Ошибка обработки')

class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name=_('проект')
    )
    original_name = models.CharField(_('оригинальное название'), max_length=255)
    
    video_file = models.FileField(
        _('файл видео'),
        upload_to=get_video_upload_path,
        null=True,
        blank=True
    )
    video_url = models.URLField(_('URL видео'), max_length=2000, null=True, blank=True)
    
    duration = models.IntegerField(_('длительность (секунды)'), default=0)
    file_size = models.BigIntegerField(_('размер файла (байты)'), default=0)
    
    status = models.CharField(
        _('статус'),
        max_length=20,
        choices=VideoStatus.choices,
        default=VideoStatus.UPLOADED,
        db_index=True
    )
    status_message = models.TextField(_('сообщение о статусе'), blank=True)
    
    ai_report = models.JSONField(_('отчет AI'), null=True, blank=True)
    processed_at = models.DateTimeField(_('дата обработки'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('видео')
        verbose_name_plural = _('видео')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.original_name or str(self.id)

    @property
    def is_processing(self):
        return self.status in [VideoStatus.UPLOADED, VideoStatus.PROCESSING, VideoStatus.VERIFICATION]

    @property
    def is_completed(self):
        return self.status == VideoStatus.COMPLETED

    @property
    def has_risks(self):
        if not self.ai_report:
            return False
        return len(self.ai_report.get('risks', [])) > 0
