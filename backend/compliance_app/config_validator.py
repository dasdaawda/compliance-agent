"""
Валидатор конфигурации для production деплоя.
Проверяет наличие всех необходимых переменных окружения.
"""
import os
import sys
from typing import List, Tuple


class ConfigValidator:
    """Валидатор конфигурации приложения."""
    
    REQUIRED_VARS = [
        'SECRET_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'REPLICATE_API_TOKEN',
        'BACKBLAZE_ENDPOINT_URL',
        'BACKBLAZE_APPLICATION_KEY_ID',
        'BACKBLAZE_APPLICATION_KEY',
        'BACKBLAZE_BUCKET_NAME',
    ]
    
    RECOMMENDED_VARS = [
        'CLOUDFLARE_CDN_URL',
        'EMAIL_HOST',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
    ]
    
    SECURITY_VARS = [
        ('SECRET_KEY', 'unsafe-secret-key'),
        ('SECRET_KEY', 'django-insecure-'),
    ]
    
    @classmethod
    def validate_production(cls) -> Tuple[bool, List[str]]:
        """
        Валидирует конфигурацию для production.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        warnings = []
        
        # Проверяем DEBUG режим
        debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
        if debug:
            warnings.append("⚠️  WARNING: DEBUG=True в production небезопасно!")
        
        # Проверяем обязательные переменные
        for var in cls.REQUIRED_VARS:
            value = os.getenv(var)
            if not value:
                errors.append(f"❌ ОШИБКА: Не задана обязательная переменная {var}")
            elif value.strip() == '':
                errors.append(f"❌ ОШИБКА: Переменная {var} пуста")
        
        # Проверяем рекомендуемые переменные
        for var in cls.RECOMMENDED_VARS:
            value = os.getenv(var)
            if not value:
                warnings.append(f"⚠️  ПРЕДУПРЕЖДЕНИЕ: Не задана рекомендуемая переменная {var}")
        
        # Проверяем безопасность
        for var, unsafe_value in cls.SECURITY_VARS:
            value = os.getenv(var, '')
            if unsafe_value in value:
                errors.append(
                    f"❌ ОШИБКА БЕЗОПАСНОСТИ: {var} содержит небезопасное значение! "
                    f"Сгенерируйте новый SECRET_KEY для production."
                )
        
        # Проверяем формат URL
        database_url = os.getenv('DATABASE_URL', '')
        if database_url and not database_url.startswith(('postgres://', 'postgresql://')):
            errors.append(
                f"❌ ОШИБКА: DATABASE_URL должен начинаться с postgres:// или postgresql://"
            )
        
        redis_url = os.getenv('REDIS_URL', '')
        if redis_url and not redis_url.startswith(('redis://', 'rediss://')):
            errors.append(
                f"❌ ОШИБКА: REDIS_URL должен начинаться с redis:// или rediss://"
            )
        
        # Проверяем Replicate токен
        replicate_token = os.getenv('REPLICATE_API_TOKEN', '')
        if replicate_token and not replicate_token.startswith('r8_'):
            warnings.append(
                f"⚠️  ПРЕДУПРЕЖДЕНИЕ: REPLICATE_API_TOKEN должен начинаться с 'r8_'. "
                f"Проверьте правильность токена."
            )
        
        # Проверяем Backblaze endpoint
        b2_endpoint = os.getenv('BACKBLAZE_ENDPOINT_URL', '')
        if b2_endpoint and not b2_endpoint.startswith('https://s3.'):
            warnings.append(
                f"⚠️  ПРЕДУПРЕЖДЕНИЕ: BACKBLAZE_ENDPOINT_URL должен начинаться с 'https://s3.'. "
                f"Текущее значение: {b2_endpoint}"
            )
        
        # Выводим результаты
        if errors or warnings:
            print("\n" + "="*60)
            print("📋 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ КОНФИГУРАЦИИ")
            print("="*60 + "\n")
        
        if errors:
            print("🚨 КРИТИЧЕСКИЕ ОШИБКИ:")
            for error in errors:
                print(f"  {error}")
            print()
        
        if warnings:
            print("⚠️  ПРЕДУПРЕЖДЕНИЯ:")
            for warning in warnings:
                print(f"  {warning}")
            print()
        
        is_valid = len(errors) == 0
        
        if is_valid:
            if not warnings:
                print("✅ Конфигурация валидна! Все переменные заданы корректно.\n")
            else:
                print("✅ Конфигурация валидна (с предупреждениями).\n")
        else:
            print("❌ Конфигурация невалидна! Исправьте ошибки перед запуском.\n")
            print("💡 Подсказка: Проверьте файл .env или переменные окружения.")
            print("💡 Пример: .env.example\n")
        
        return is_valid, errors + warnings
    
    @classmethod
    def validate_or_exit(cls):
        """
        Валидирует конфигурацию и завершает процесс при ошибках.
        Используется при запуске приложения.
        """
        # Пропускаем валидацию для команд управления Django
        if len(sys.argv) > 1 and sys.argv[1] in [
            'makemigrations', 'migrate', 'shell', 'createsuperuser', 
            'collectstatic', 'check', 'showmigrations'
        ]:
            return
        
        # Пропускаем в DEBUG режиме (для разработки)
        debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
        if debug:
            print("ℹ️  DEBUG режим: пропуск валидации конфигурации\n")
            return
        
        is_valid, messages = cls.validate_production()
        
        if not is_valid:
            print("="*60)
            print("🛑 ПРИЛОЖЕНИЕ НЕ МОЖЕТ ЗАПУСТИТЬСЯ")
            print("="*60)
            print("\nИсправьте ошибки конфигурации и попробуйте снова.\n")
            sys.exit(1)


def validate_config():
    """Точка входа для валидации конфигурации."""
    ConfigValidator.validate_or_exit()


if __name__ == '__main__':
    is_valid, _ = ConfigValidator.validate_production()
    sys.exit(0 if is_valid else 1)
