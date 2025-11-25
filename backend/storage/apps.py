from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class StorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'storage'
    verbose_name = 'Хранилище'

    def ready(self):
        # Импорт сигналов при старте приложения (без критической ошибки, если их нет)
        try:
            from . import signals  # noqa: F401
        except Exception:
            logger.debug("No storage signals to register or failed to import them.", exc_info=True)