import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from projects.models import Video
from ai_pipeline.models import AITrigger
from users.models import UserRole


class OperatorActionLog(models.Model):
    """Лог действий операторов для аудита"""
    class ActionType(models.TextChoices):
        ASSIGNED_TASK = 'assigned_task', _('Назначен задачу')
        HEARTBEAT = 'heartbeat', _('Обновил активность')
        COMPLETED_TASK = 'completed_task', _('Завершил задачу')
        RELEASED_TASK = 'released_task', _('Освободил задачу')
        PROCESSED_TRIGGER = 'processed_trigger', _('Обработал триггер')
        RESUMED_TASK = 'resumed_task', _('Возобновил задачу')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='action_logs',
        verbose_name=_('оператор')
    )
    task = models.ForeignKey(
        'ai_pipeline.VerificationTask',
        on_delete=models.CASCADE,
        related_name='action_logs',
        null=True,
        blank=True,
        verbose_name=_('задача')
    )
    trigger = models.ForeignKey(
        AITrigger,
        on_delete=models.CASCADE,
        related_name='action_logs',
        null=True,
        blank=True,
        verbose_name=_('триггер')
    )
    action_type = models.CharField(_('тип действия'), max_length=20, choices=ActionType.choices)
    details = models.JSONField(_('детали'), default=dict, blank=True)
    timestamp = models.DateTimeField(_('время действия'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('лог действия оператора')
        verbose_name_plural = _('логи действий операторов')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['operator', '-timestamp']),
            models.Index(fields=['task', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.operator.username} - {self.get_action_type_display()} - {self.timestamp}"


class OperatorLabel(models.Model):
    class FinalLabel(models.TextChoices):
        OK = "ok", _("OK")
        OK_FALSE = "ok_false", _("OK (ложное срабатывание)")
        AD_BRAND = "reklama_brand", _("Реклама (бренд)")
        PROFANITY_SPEECH = "mat_speech", _("Мат (речь)")
        PORNOGRAPHY_18 = "nsfw_18", _("Порнография (18+)")
        VIOLENCE_18 = "violence_18", _("Насилие (18+)")
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        SUBMITTED = 'submitted', _('Отправлено')
        APPROVED = 'approved', _('Утверждено')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='operator_labels', verbose_name=_('видео'))
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_labels',
        verbose_name=_('оператор'),
        limit_choices_to={'role': UserRole.OPERATOR}
    )
    ai_trigger = models.ForeignKey(
        AITrigger,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='operator_decisions',
        verbose_name=_('AI триггер')
    )
    
    start_time_sec = models.DecimalField(_('время начала (сек)'), max_digits=10, decimal_places=3)
    end_time_sec = models.DecimalField(
        _('время окончания (сек)'),
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text=_('Конец временного интервала метки')
    )
    final_label = models.CharField(_('финальная метка'), max_length=50, choices=FinalLabel.choices, db_index=True)
    confidence = models.DecimalField(
        _('уверенность оператора'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Уверенность оператора в решении (0-100)')
    )
    status = models.CharField(
        _('статус'),
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True
    )
    comment = models.TextField(_('комментарий'), blank=True)
    
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('метка оператора')
        verbose_name_plural = _('метки операторов')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['final_label']),
            models.Index(fields=['status']),
            models.Index(fields=['video', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['video', 'ai_trigger', 'operator'],
                name='unique_video_trigger_operator'
            )
        ]

    def __str__(self):
        return f"{self.get_final_label_display()} @ {self.start_time_sec}s"
