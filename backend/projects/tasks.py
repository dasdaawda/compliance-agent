import logging
logger = logging.getLogger(__name__)

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_video_ready_notification(video_id):
    from .models import Video
    try:
        video = Video.objects.get(id=video_id)
        client = getattr(video.project, 'owner', None)
        recipient = getattr(client, 'email', None)

        if not recipient:
            logger.warning("No recipient email for video %s (project owner missing or has no email)", video_id)
            return False

        subject = f"Отчет по видео готов: {video.original_name}"
        message = f"Ваше видео '{video.original_name}' обработано. Проверьте отчет в личном кабинете."
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ai-compliance.com')

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[recipient],
            fail_silently=False,
        )

        logger.info("Notification sent for video %s to %s", video_id, recipient)
        return True
    except Video.DoesNotExist:
        logger.error("Failed to send notification: Video not found (%s)", video_id)
        return False
    except Exception as e:
        logger.exception("Failed to send notification for video %s: %s", video_id, e)
        return False