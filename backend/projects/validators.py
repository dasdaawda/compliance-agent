import logging
import os
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class VideoValidationError(Exception):
    """Exception raised when video validation fails."""
    pass


class VideoValidator:
    """Validates video files before pipeline processing."""

    def __init__(self):
        self.max_file_size = getattr(settings, 'MAX_VIDEO_FILE_SIZE', 2147483648)  # 2GB
        self.max_duration = getattr(settings, 'MAX_VIDEO_DURATION', 7200)  # 2 hours
        self.allowed_formats = getattr(settings, 'ALLOWED_VIDEO_FORMATS', ['mp4', 'avi', 'mov', 'mkv', 'webm'])

    def validate_video(self, video):
        """
        Validates a video object before processing.
        Raises VideoValidationError if validation fails.
        """
        errors = []

        # Check file size
        if video.file_size and video.file_size > self.max_file_size:
            errors.append(
                f"File size {video.file_size} bytes exceeds maximum {self.max_file_size} bytes "
                f"({self.max_file_size / (1024**3):.2f} GB)"
            )

        # Check duration
        if video.duration and video.duration > self.max_duration:
            errors.append(
                f"Video duration {video.duration} seconds exceeds maximum {self.max_duration} seconds "
                f"({self.max_duration / 3600:.1f} hours)"
            )

        # Check format
        if video.original_name:
            ext = video.original_name.split('.')[-1].lower()
            if ext not in self.allowed_formats:
                errors.append(
                    f"File format '.{ext}' not allowed. Supported formats: {', '.join(self.allowed_formats)}"
                )

        # Check file existence for file-based videos
        if video.video_file:
            file_path = video.video_file.path
            if not os.path.exists(file_path):
                errors.append(f"Video file not found at {file_path}")

        if errors:
            error_message = "; ".join(errors)
            logger.error(f"Video validation failed for {video.id}: {error_message}")
            raise VideoValidationError(error_message)

        logger.info(f"Video validation passed for {video.id}")
        return True

    def validate_file_path(self, file_path):
        """
        Validates a file path for video processing.
        Returns True if valid, raises VideoValidationError if not.
        """
        if not os.path.exists(file_path):
            raise VideoValidationError(f"File not found: {file_path}")

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            raise VideoValidationError(
                f"File size {file_size} bytes exceeds maximum {self.max_file_size} bytes"
            )

        # Check file format
        ext = file_path.split('.')[-1].lower()
        if ext not in self.allowed_formats:
            raise VideoValidationError(f"File format '.{ext}' not allowed")

        return True


def notify_validation_failure(video, error_message):
    """
    Sends notification email to project owner about validation failure.
    """
    try:
        client = getattr(video.project, 'owner', None)
        recipient = getattr(client, 'email', None) if client else None
        admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@localhost')

        if not recipient:
            logger.warning(
                f"No recipient email for video {video.id} (project owner missing or has no email)"
            )
            recipient = admin_email

        subject = f"❌ Ошибка валидации видео: {video.original_name}"
        message = (
            f"Видео '{video.original_name}' не прошло валидацию и не может быть обработано.\n\n"
            f"Ошибка: {error_message}\n\n"
            f"Пожалуйста, проверьте параметры видео и попробуйте снова."
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ai-compliance.com')

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[recipient],
            fail_silently=False,
        )

        logger.info(f"Validation failure notification sent for video {video.id} to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send validation failure notification for video {video.id}: {e}")
        return False
