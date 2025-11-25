from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Пользователи'

    def ready(self):
        # Импорт сигналов при старте приложения (мягко игнорируем ошибки)
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass