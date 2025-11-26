import logging
logger = logging.getLogger(__name__)

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@shared_task
def send_video_ready_notification(video_id):
    """Send templated HTML email notification when video is ready for verification."""
    from .models import Video
    try:
        video = Video.objects.get(id=video_id)
        client = getattr(video.project, 'owner', None)
        recipient = getattr(client, 'email', None)

        if not recipient:
            logger.warning("No recipient email for video %s (project owner missing or has no email)", video_id)
            return False

        subject = f"✅ Отчет по видео готов: {video.original_name}"
        
        # Build HTML email
        context = {
            'video_name': video.original_name,
            'project_name': video.project.name,
            'video_id': str(video.id),
            'dashboard_url': getattr(settings, 'DASHBOARD_URL', 'https://app.example.com'),
        }
        
        try:
            html_message = render_to_string('emails/video_ready.html', context)
            plain_message = strip_tags(html_message)
        except Exception as e:
            logger.warning(f"Failed to render email template: {e}. Using plain text.")
            plain_message = (
                f"Ваше видео '{video.original_name}' обработано и готово к верификации. "
                f"Проверьте отчет в личном кабинете."
            )
            html_message = None
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ai-compliance.com')

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info("Video ready notification sent for video %s to %s", video_id, recipient)
        return True
    except Video.DoesNotExist:
        logger.error("Failed to send notification: Video not found (%s)", video_id)
        return False
    except Exception as e:
        logger.exception("Failed to send notification for video %s: %s", video_id, e)
        return False


@shared_task
def send_pipeline_failure_notification(video_id, stage, error_message):
    """Send notification email on pipeline failure to admins and project owner."""
    from .models import Video
    try:
        video = Video.objects.get(id=video_id)
        client = getattr(video.project, 'owner', None)
        owner_email = getattr(client, 'email', None) if client else None
        admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@localhost')
        
        recipient_list = []
        if owner_email:
            recipient_list.append(owner_email)
        recipient_list.append(admin_email)
        
        if not recipient_list:
            logger.warning("No recipient emails for pipeline failure notification")
            return False

        subject = f"❌ Ошибка обработки видео: {video.original_name} ({stage})"
        
        message = (
            f"Видео '{video.original_name}' не удалось обработать.\n\n"
            f"Этап сбоя: {stage}\n"
            f"Сообщение об ошибке: {error_message}\n\n"
            f"ID видео: {video_id}\n"
            f"Проект: {video.project.name}\n\n"
            f"Пожалуйста, проверьте логи для получения дополнительной информации."
        )
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ai-compliance.com')

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )

        logger.info(
            f"Pipeline failure notification sent for video {video_id} "
            f"(stage: {stage}) to {recipient_list}"
        )
        return True
    except Video.DoesNotExist:
        logger.error("Failed to send failure notification: Video not found (%s)", video_id)
        return False
    except Exception as e:
        logger.exception("Failed to send pipeline failure notification for video %s: %s", video_id, e)
        return False