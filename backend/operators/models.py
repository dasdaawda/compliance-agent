import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from projects.models import Video
from ai_pipeline.models import AITrigger
from users.models import UserRole


class OperatorLabel(models.Model):
    class FinalLabel(models.TextChoices):
        OK = "ok", _("OK")
        OK_FALSE = "ok_false", _("OK (ложное срабатывание)")
        AD_BRAND = "reklama_brand", _("Реклама (бренд)")
        PROFANITY_SPEECH = "mat_speech", _("Мат (речь)")
        PORNOGRAPHY_18 = "nsfw_18", _("Порнография (18+)")
        VIOLENCE_18 = "violence_18", _("Насилие (18+)")

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
    final_label = models.CharField(_('финальная метка'), max_length=50, choices=FinalLabel.choices, db_index=True)
    comment = models.TextField(_('комментарий'), blank=True)
    
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('метка оператора')
        verbose_name_plural = _('метки операторов')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_final_label_display()} @ {self.start_time_sec}s"
