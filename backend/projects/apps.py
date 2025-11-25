from django.apps import AppConfig

class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'
    verbose_name = 'Проекты'

    def ready(self):
        # Пример: импорт сигналов для регистрации при старте приложения
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass