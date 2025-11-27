# ⚙️ Конфигурация приложения

## Структура настроек Django

Приложение использует модульную структуру настроек для различных окружений:

```
backend/compliance_app/settings/
├── __init__.py      # Автоматический выбор окружения по DJANGO_ENV
├── base.py          # Общие настройки для всех окружений
├── dev.py           # Настройки разработки (DEBUG=True)
└── prod.py          # Настройки production (безопасность, валидация)
```

### Выбор окружения

Окружение определяется переменной `DJANGO_ENV`:

```bash
# Для разработки
export DJANGO_ENV=development

# Для production (по умолчанию)
export DJANGO_ENV=production

# Или через .env файл
echo "DJANGO_ENV=development" >> .env
```

**Важно:** `DJANGO_SETTINGS_MODULE` всегда указывает на `compliance_app.settings`, а выбор конкретного файла (dev/prod) происходит автоматически через `__init__.py`.

### Development (dev.py)

- `DEBUG = True`
- `ALLOWED_HOSTS = ['*']`
- SQLite по умолчанию (или PostgreSQL через DATABASE_URL)
- Email в консоль
- Без HTTPS redirect
- Replicate токен не обязателен

### Production (prod.py)

- `DEBUG = False` (обязательно)
- `ALLOWED_HOSTS` должен быть задан
- PostgreSQL обязателен
- SMTP email обязателен
- HTTPS redirects включены
- Валидация всех критических переменных
- Сжатие статических файлов (WhiteNoise)

## Быстрый старт

### 1. Создайте файл конфигурации

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Или используйте скрипт быстрой настройки
./setup_env.sh
```

### 2. Заполните обязательные переменные

Откройте `.env` и заполните следующие переменные:

```env
# Django
SECRET_KEY=ваш-уникальный-секретный-ключ
DEBUG=False
ALLOWED_HOSTS=yourdomain.com

# Database
DATABASE_URL=postgres://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Backblaze B2
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=your_key_id
BACKBLAZE_APPLICATION_KEY=your_application_key
BACKBLAZE_BUCKET_NAME=your-bucket-name

# Replicate
REPLICATE_API_TOKEN=r8_your_token_here
```

### 3. Проверьте конфигурацию

```bash
python backend/compliance_app/config_validator.py
```

Если все настроено правильно, вы увидите:
```
✅ Конфигурация валидна! Все переменные заданы корректно.
```

---

## Переменные окружения

### Обязательные переменные

Эти переменные **ОБЯЗАТЕЛЬНЫ** для работы приложения в production:

| Переменная | Описание | Пример |
|------------|----------|---------|
| `DJANGO_ENV` | Окружение (development/production) | `production` |
| `SECRET_KEY` | Секретный ключ Django | `django-insecure-abc123...` |
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | URL подключения к Redis | `redis://localhost:6379/0` |
| `REPLICATE_API_TOKEN` | API токен Replicate | `r8_abc123...` |
| `BACKBLAZE_ENDPOINT_URL` | Endpoint URL Backblaze B2 | `https://s3.us-west-000.backblazeb2.com` |
| `BACKBLAZE_APPLICATION_KEY_ID` | Key ID для B2 | `000abc123...` |
| `BACKBLAZE_APPLICATION_KEY` | Application Key для B2 | `K000AbC...` |
| `BACKBLAZE_BUCKET_NAME` | Имя бакета в B2 | `ai-compliance-videos` |

### Рекомендуемые переменные

Эти переменные не обязательны, но **настоятельно рекомендуются** для production:

| Переменная | Описание | Пример |
|------------|----------|---------|
| `CLOUDFLARE_CDN_URL` | URL Cloudflare CDN для B2 | `https://cdn.yourdomain.com` |
| `EMAIL_HOST` | SMTP сервер | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP порт | `587` |
| `EMAIL_HOST_USER` | SMTP пользователь | `your-email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | SMTP пароль | `your-app-password` |
| `DEFAULT_FROM_EMAIL` | Email отправителя | `noreply@yourdomain.com` |

### Опциональные переменные

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DEBUG` | Режим отладки | `False` |
| `ALLOWED_HOSTS` | Разрешенные хосты | `localhost` |
| `MAX_VIDEO_FILE_SIZE` | Макс. размер видео (байты) | `2147483648` (2GB) |
| `MAX_VIDEO_DURATION` | Макс. длительность (сек) | `7200` (2 часа) |
| `FRAME_EXTRACTION_FPS` | FPS для извлечения кадров | `1` |
| `REPLICATE_TIMEOUT` | Timeout API (сек) | `300` |
| `TEMP_DIR` | Директория для временных файлов | `/tmp` |

---

## Получение API ключей

### Backblaze B2

1. Зарегистрируйтесь на https://www.backblaze.com/b2/sign-up.html
2. Создайте бакет: **Buckets → Create a Bucket**
   - Bucket Name: `ai-compliance-videos`
   - Files in Bucket: **Private**
3. Создайте Application Key: **App Keys → Add a New Application Key**
   - Key Name: `ai-compliance-production`
   - Allow access to: **All**
   - Type of Access: **Read and Write**
4. Сохраните:
   - `keyID` → `BACKBLAZE_APPLICATION_KEY_ID`
   - `applicationKey` → `BACKBLAZE_APPLICATION_KEY`
5. Найдите Endpoint в разделе **Buckets → Endpoint**

### Replicate

1. Зарегистрируйтесь на https://replicate.com
2. Перейдите в https://replicate.com/account/api-tokens
3. Создайте новый токен или скопируйте существующий
4. Токен начинается с `r8_`

### Cloudflare (опционально)

1. Зарегистрируйтесь на https://cloudflare.com
2. Добавьте ваш домен
3. Настройте DNS:
   - CNAME: `cdn` → `f000.backblazeb2.com` (из настроек B2)
   - Proxy status: **Proxied** (оранжевое облако)
4. Создайте API токен: https://dash.cloudflare.com/profile/api-tokens
   - Permissions: Zone - Cache Purge, Zone - Zone Read
5. Скопируйте Zone ID из дашборда вашего домена

### Email (Gmail пример)

1. Включите двухфакторную аутентификацию
2. Создайте App Password: https://myaccount.google.com/apppasswords
3. Используйте сгенерированный пароль в `EMAIL_HOST_PASSWORD`

**Альтернативы:** SendGrid, Mailgun, AWS SES, Mailjet

---

## AI Модели

По умолчанию используются следующие модели:

| Модель | Назначение | ID |
|--------|------------|----|
| OpenAI Whisper Small | Распознавание речи (ASR) | `openai/whisper:4d50...` |
| YOLOv8 | Детекция объектов | `adirik/yolov8:...` |
| NSFW Detection | Детекция 18+ контента | `lucataco/nsfw-image-detection:...` |
| Violence Detection | Детекция жести/насилия | `lucataco/vit-violence-detection:...` |
| EasyOCR | Распознавание текста | `abiruyt/text-extract-ocr:...` |

Вы можете переопределить модели, задав соответствующие переменные:

```env
WHISPER_MODEL_ID=your-custom-whisper-model
YOLO_MODEL_ID=your-custom-yolo-model
NSFW_MODEL_ID=your-custom-nsfw-model
VIOLENCE_MODEL_ID=your-custom-violence-model
OCR_MODEL_ID=your-custom-ocr-model
```

---

## Проверка конфигурации

### Автоматическая валидация

При запуске приложения в production режиме (DEBUG=False) автоматически запускается валидация конфигурации. Если обязательные переменные не заданы, приложение не запустится.

### Ручная проверка

Вы можете вручную проверить конфигурацию:

```bash
python backend/compliance_app/config_validator.py
```

Результат:
```
📋 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ КОНФИГУРАЦИИ
====================================

✅ Конфигурация валидна! Все переменные заданы корректно.
```

Или с ошибками:
```
🚨 КРИТИЧЕСКИЕ ОШИБКИ:
  ❌ ОШИБКА: Не задана обязательная переменная REPLICATE_API_TOKEN
  ❌ ОШИБКА БЕЗОПАСНОСТИ: SECRET_KEY содержит небезопасное значение!

⚠️  ПРЕДУПРЕЖДЕНИЯ:
  ⚠️  WARNING: DEBUG=True в production небезопасно!
  ⚠️  ПРЕДУПРЕЖДЕНИЕ: Не задана рекомендуемая переменная EMAIL_HOST
```

---

## Генерация SECRET_KEY

Никогда не используйте дефолтный `SECRET_KEY` в production!

```bash
# Генерация нового ключа
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Скопируйте результат в `.env`:
```env
SECRET_KEY=generated-secret-key-here
```

---

## Примеры конфигураций

### Локальная разработка

```env
DEBUG=True
SECRET_KEY=dev-secret-key
DATABASE_URL=postgres://postgres:postgres@localhost:5432/ai_compliance_dev
REDIS_URL=redis://localhost:6379/0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Минимальные настройки для тестирования
REPLICATE_API_TOKEN=dummy_token
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=test_key_id
BACKBLAZE_APPLICATION_KEY=test_key
BACKBLAZE_BUCKET_NAME=test-bucket
```

### Production на DigitalOcean

```env
DEBUG=False
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=yourapp.ondigitalocean.app,.yourdomain.com

# Managed databases (автоматически)
DATABASE_URL=${db.DATABASE_URL}
REDIS_URL=${redis.REDIS_URL}

# Backblaze B2
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=${BACKBLAZE_KEY_ID}
BACKBLAZE_APPLICATION_KEY=${BACKBLAZE_KEY}
BACKBLAZE_BUCKET_NAME=ai-compliance-production

# Cloudflare CDN
CLOUDFLARE_CDN_URL=https://cdn.yourdomain.com

# Replicate
REPLICATE_API_TOKEN=${REPLICATE_TOKEN}

# Email (SendGrid)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=${SENDGRID_API_KEY}
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Production optimizations
TEMP_DIR=/tmp
MAX_VIDEO_FILE_SIZE=2147483648
FRAME_EXTRACTION_FPS=1
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
```

---

## Troubleshooting

### Ошибка: "REPLICATE_API_TOKEN must be set"

**Решение:** Задайте токен Replicate в `.env`:
```env
REPLICATE_API_TOKEN=r8_your_token_here
```

### Ошибка: "Backblaze credentials missing"

**Решение:** Проверьте, что все 4 переменные B2 заданы:
```env
BACKBLAZE_ENDPOINT_URL=...
BACKBLAZE_APPLICATION_KEY_ID=...
BACKBLAZE_APPLICATION_KEY=...
BACKBLAZE_BUCKET_NAME=...
```

### Ошибка: "Cannot connect to database"

**Решение:** Проверьте формат `DATABASE_URL`:
```env
# Правильно:
DATABASE_URL=postgres://user:password@host:5432/dbname

# Неправильно:
DATABASE_URL=postgresql://...  # (тоже работает, но предпочтительнее postgres://)
```

### Ошибка: "Cannot connect to Redis"

**Решение:** Проверьте `REDIS_URL`:
```env
# Правильно:
REDIS_URL=redis://localhost:6379/0

# Для Redis с SSL:
REDIS_URL=rediss://default:password@host:25061
```

---

## Pipeline Resilience и Storage Settings

### Retry Configuration

Параметры автоматического повтора для задач хранилища B2:

```env
# B2 retry settings
B2_MAX_RETRIES=3                    # Максимум попыток (по умолчанию: 3)
B2_RETRY_BACKOFF=2                  # Множитель экспоненциального backoff (по умолчанию: 2)
B2_RETRY_BACKOFF_MAX=60             # Максимальное время ожидания между попытками (секунды, по умолчанию: 60)
```

### Validation Settings

Параметры валидации видео перед обработкой:

```env
# Ограничения размера и длительности
MAX_VIDEO_FILE_SIZE=2147483648      # Максимальный размер файла (байты, по умолчанию: 2GB)
MAX_VIDEO_DURATION=7200             # Максимальная длительность (секунды, по умолчанию: 2 часа)
ALLOWED_VIDEO_FORMATS=mp4,avi,mov,mkv,webm  # Допустимые форматы (по умолчанию: mp4, avi, mov, mkv, webm)
```

### Artifact Retention Policies

Автоматическое удаление старых артефактов:

- **Завершенные пайплайны** удаляются из B2 через **7 дней** после завершения
- **Неудачные пайплайны** удаляются через **14 дней** (для анализа ошибок)
- **Временные файлы** (кадры, аудио) удаляются через **24 часа** после завершения отчета
- **Кэшированные URL** истекают через **1 час** (переиспользование не рекомендуется)

Периодические задачи:
- `cleanup_artifacts_periodic`: Очистка артефактов (запускается ежедневно в 2:00 UTC)
- `refresh_cdn_cache_periodic`: Обновление CDN кэша (запускается каждый час)

---

## Pipeline Error Handling

### Fail-Fast Validation

Видео валидируется перед запуском пайплайна:
- Проверка размера файла
- Проверка длительности
- Проверка формата файла
- Проверка наличия файла

Если валидация не пройдена, отправляется уведомление на email и видео помечается как `FAILED`.

### Structured Logging

Все этапы пайплайна логируются в JSON формате для удобства отладки:

```json
{
  "timestamp": "2024-01-01T12:00:00.000000",
  "video_id": "uuid-here",
  "step": "preprocess_video",
  "status": "completed",
  "error": null
}
```

### Notifications

#### Success Notifications

Когда отчет готов к верификации, отправляется HTML письмо:
- **Получатели:** Владелец проекта
- **Шаблон:** `emails/video_ready.html`
- **Тема:** ✅ Отчет по видео готов

#### Failure Notifications

При сбое пайплайна отправляется уведомление:
- **Получатели:** Владелец проекта + администратор
- **Информация:** Этап сбоя, сообщение об ошибке, ID видео
- **Тема:** ❌ Ошибка обработки видео

---

## Storage с B2 Retries

### B2Utils Wrapper

Все операции с Backblaze B2 используют обертку `B2Utils`:

```python
from storage.b2_utils import get_b2_utils

b2_utils = get_b2_utils()

# Upload video
url = b2_utils.upload_video('/local/path/video.mp4', 'videos/id.mp4')

# Generate signed URL (с кэшированием)
signed_url = b2_utils.generate_signed_url('videos/id.mp4')

# Delete artifact
b2_utils.delete_artifact('videos/id.mp4')
```

### Retry Logic

- **Автоматические повторы** на ClientError и OSError
- **Экспоненциальный backoff**: 1s, 2s, 4s, ..., до 60s
- **Максимум попыток:** 3 (настраивается)
- **Логирование:** Каждая попытка логируется

### Signed URL Caching

- Кэшированные URL хранятся в Redis
- TTL: 1 час
- Автоматическое очищение при удалении артефакта

---

## Дополнительная документация

- **Деплой:** См. [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Архитектура:** См. [ARCHITECTURE_IMPROVEMENTS.md](ARCHITECTURE_IMPROVEMENTS.md)
- **Исправления:** См. [CRITICAL_FIXES_EXAMPLES.md](CRITICAL_FIXES_EXAMPLES.md)

---

## Безопасность

⚠️ **ВАЖНО:**

- **Никогда** не коммитьте файл `.env` в репозиторий!
- **Всегда** генерируйте уникальный `SECRET_KEY` для production
- **Используйте** `DEBUG=False` в production
- **Храните** чувствительные данные в секретах (не в коде)
- **Используйте** SSL для PostgreSQL и Redis в production
- **Ограничьте** доступ к B2 бакету (Private buckets)

Файл `.env` уже добавлен в `.gitignore`.
