# 🚀 Руководство по деплою AI-Комплаенс Агент

## Содержание
1. [Подготовка к деплою](#подготовка-к-деплою)
2. [Настройка переменных окружения](#настройка-переменных-окружения)
3. [Деплой на DigitalOcean App Platform](#деплой-на-digitalocean-app-platform)
4. [Настройка внешних сервисов](#настройка-внешних-сервисов)
5. [Проверка работоспособности](#проверка-работоспособности)
6. [Troubleshooting](#troubleshooting)

---

## Подготовка к деплою

### 1. Предварительные требования

Перед началом убедитесь, что у вас есть:

- ✅ Аккаунт DigitalOcean
- ✅ Аккаунт Backblaze B2
- ✅ Аккаунт Replicate.com
- ✅ Аккаунт Cloudflare (опционально, но рекомендуется)
- ✅ Email сервис (Gmail, SendGrid, Mailgun или др.)

### 2. Создайте конфигурационный файл

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Откройте файл для редактирования
nano .env
```

---

## Настройка переменных окружения

### Обязательные переменные (без них приложение не запустится)

#### 1. Django Core
```env
SECRET_KEY=ваш-секретный-ключ-сгенерируйте-его
DEBUG=False
ALLOWED_HOSTS=.yourdomain.com,yourapp-xxxxx.ondigitalocean.app
```

**Генерация SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### 2. База данных PostgreSQL
```env
DATABASE_URL=postgres://user:password@host:port/database_name?sslmode=require
```

**Где взять:**
- DigitalOcean: Managed Databases → PostgreSQL → Connection Details → "Connection String"

#### 3. Redis
```env
REDIS_URL=rediss://default:password@host:port
```

**Где взять:**
- DigitalOcean: Managed Databases → Redis → Connection Details → "Redis URI"

#### 4. Backblaze B2
```env
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=000abc123def4567890
BACKBLAZE_APPLICATION_KEY=K000AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
BACKBLAZE_BUCKET_NAME=ai-compliance-videos
```

**Как получить:**
1. Перейдите на https://secure.backblaze.com/
2. Выберите **App Keys** → **Add a New Application Key**
3. Выберите доступ: **Read and Write**
4. Скопируйте `keyID` → `BACKBLAZE_APPLICATION_KEY_ID`
5. Скопируйте `applicationKey` → `BACKBLAZE_APPLICATION_KEY`
6. Endpoint найдите в разделе **Buckets** → **Endpoint**

**Создание бакета:**
```bash
# В веб-интерфейсе B2:
1. Buckets → Create a Bucket
2. Bucket Unique Name: ai-compliance-videos
3. Files in Bucket: Private
4. Object Lock: Disabled
5. Create Bucket
```

#### 5. Replicate API
```env
REPLICATE_API_TOKEN=r8_ваш_токен_replicate
```

**Как получить:**
1. Перейдите на https://replicate.com/account/api-tokens
2. Создайте новый токен или скопируйте существующий
3. Токен начинается с `r8_`

---

### Опциональные (но рекомендуемые) переменные

#### 6. Cloudflare CDN (для бесплатного egress-трафика)

```env
CLOUDFLARE_CDN_URL=https://cdn.yourdomain.com
CLOUDFLARE_API_TOKEN=ваш_cloudflare_api_token
CLOUDFLARE_ZONE_ID=ваш_zone_id
```

**Настройка Cloudflare + Backblaze B2:**

1. **Добавьте домен в Cloudflare:**
   - DNS → Add record → CNAME
   - Name: `cdn`
   - Target: `f000.backblazeb2.com` (из настроек B2 бакета)
   - Proxy status: **Proxied** (оранжевое облако)

2. **Настройте B2 для работы с Cloudflare:**
   ```bash
   # В настройках бакета B2:
   Bucket Settings → Bucket Info → "Friendly URL"
   ```

3. **Получите Cloudflare API Token:**
   - https://dash.cloudflare.com/profile/api-tokens
   - Create Token → Custom Token
   - Permissions: Zone - Cache Purge, Zone - Zone Read
   - Zone Resources: Include - Specific zone - yourdomain.com

4. **Найдите Zone ID:**
   - Cloudflare Dashboard → Ваш домен → Правая панель → Zone ID

#### 7. Email (для уведомлений)

**Вариант A: Gmail (для тестирования)**
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

⚠️ **Gmail требует "App Password":** https://myaccount.google.com/apppasswords

**Вариант B: SendGrid (рекомендуется для production)**
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.ваш_sendgrid_api_key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

**Вариант C: AWS SES**
```env
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_HOST_USER=ваш_SMTP_username
EMAIL_HOST_PASSWORD=ваш_SMTP_password
```

---

## Деплой на DigitalOcean App Platform

### Шаг 1: Создание приложения

1. **Перейдите в DigitalOcean Dashboard:**
   - https://cloud.digitalocean.com/apps

2. **Создайте новое приложение:**
   - Create App → GitHub → Выберите ваш репозиторий
   - Branch: `main` (или ваша production ветка)

### Шаг 2: Конфигурация компонентов

**Компонент 1: Web Service (Django)**

```yaml
Name: web
Type: Web Service
Source: Dockerfile
HTTP Port: 8000
Run Command: gunicorn --bind 0.0.0.0:8000 --workers 2 compliance_app.wsgi:application
Health Check: /admin/login/
Instance Size: Basic (1GB RAM, 1 vCPU) - $12/mo
Instance Count: 1
```

**Компонент 2: Worker (Celery)**

```yaml
Name: celery-worker
Type: Worker
Source: Dockerfile
Run Command: celery -A compliance_app worker --loglevel=info --concurrency=2
Instance Size: Basic (1GB RAM, 1 vCPU) - $12/mo
Instance Count: 1
```

### Шаг 3: Добавление Managed Databases

**PostgreSQL:**
```yaml
Name: db
Engine: PostgreSQL 15
Size: Development (1GB RAM, 1 vCPU, 10GB SSD) - $12/mo
```

**Redis:**
```yaml
Name: redis
Engine: Redis 7
Size: Development (1GB RAM, 1 vCPU) - $15/mo
```

### Шаг 4: Настройка Environment Variables

В DigitalOcean App Platform:

1. **Settings → App-Level Environment Variables**
2. **Добавьте все переменные из вашего `.env` файла**

```env
# Django Core
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${APP_URL},.ondigitalocean.app

# Database (автоматически из Managed Database)
DATABASE_URL=${db.DATABASE_URL}

# Redis (автоматически из Managed Database)
REDIS_URL=${redis.REDIS_URL}

# Backblaze B2
BACKBLAZE_ENDPOINT_URL=${BACKBLAZE_ENDPOINT_URL}
BACKBLAZE_APPLICATION_KEY_ID=${BACKBLAZE_APPLICATION_KEY_ID}
BACKBLAZE_APPLICATION_KEY=${BACKBLAZE_APPLICATION_KEY}
BACKBLAZE_BUCKET_NAME=${BACKBLAZE_BUCKET_NAME}

# Cloudflare
CLOUDFLARE_CDN_URL=${CLOUDFLARE_CDN_URL}
CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
CLOUDFLARE_ZONE_ID=${CLOUDFLARE_ZONE_ID}

# Replicate
REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=${EMAIL_HOST}
EMAIL_PORT=${EMAIL_PORT}
EMAIL_USE_TLS=True
EMAIL_HOST_USER=${EMAIL_HOST_USER}
EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}
DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL}

# Pipeline
TEMP_DIR=/tmp
MAX_VIDEO_FILE_SIZE=2147483648
MAX_VIDEO_DURATION=7200
FRAME_EXTRACTION_FPS=1
```

⚠️ **Важно:** Используйте `${db.DATABASE_URL}` и `${redis.REDIS_URL}` для автоматического подключения managed databases!

### Шаг 5: Запуск миграций

После первого деплоя выполните:

```bash
# Через DigitalOcean Console или локально
doctl apps create-deployment YOUR_APP_ID --wait

# Подключитесь к web компоненту:
# App → web → Console → Run Command

python backend/manage.py migrate
python backend/manage.py createsuperuser
python backend/manage.py collectstatic --noinput
```

**Или настройте Pre-Deploy Job:**

```yaml
Name: migrate
Type: Pre-Deploy Job
Run Command: |
  cd /app/backend
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
```

---

## Настройка внешних сервисов

### 1. Backblaze B2 - CORS Configuration

Для работы видеоплеера необходимо настроить CORS:

```json
[
  {
    "corsRuleName": "allowVideoStreaming",
    "allowedOrigins": [
      "https://yourdomain.com",
      "https://yourapp-xxxxx.ondigitalocean.app"
    ],
    "allowedOperations": [
      "b2_download_file_by_id",
      "b2_download_file_by_name"
    ],
    "allowedHeaders": ["range"],
    "exposeHeaders": ["content-length", "content-range"],
    "maxAgeSeconds": 3600
  }
]
```

**Применение:**
```bash
# Через B2 CLI или веб-интерфейс:
Buckets → Your Bucket → Bucket Settings → CORS Rules → Add Rule
```

### 2. Cloudflare - Page Rules

Для оптимизации кэширования видео:

```yaml
URL Pattern: cdn.yourdomain.com/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
  - Browser Cache TTL: 4 hours
```

### 3. Replicate - Billing Alerts

Настройте алерты на превышение бюджета:

1. https://replicate.com/account/billing
2. **Set spending limit** → $100/month (или нужный лимит)
3. **Email notifications** → включите

---

## Проверка работоспособности

### 1. Проверка Web сервиса

```bash
# Проверьте, что приложение запущено
curl https://yourapp-xxxxx.ondigitalocean.app/admin/login/

# Ожидаемый результат: HTML страница логина Django Admin
```

### 2. Проверка базы данных

```bash
# В консоли app:
python backend/manage.py dbshell
# Должно открыться PostgreSQL соединение
```

### 3. Проверка Celery Worker

```bash
# В логах celery-worker компонента должны быть:
[INFO] celery@hostname ready.
[INFO] Connected to redis://...
```

### 4. Проверка Backblaze B2

```bash
# Загрузите тестовое видео через UI
# Проверьте в B2 бакете наличие файла в:
# videos/raw/{project_id}/{video_id}.mp4
```

### 5. Проверка Replicate API

```bash
# Создайте тестовое видео для обработки
# В логах должны быть вызовы к Replicate:
[INFO] Starting AI pipeline for video ...
[INFO] Whisper ASR completed for video ...
```

---

## Troubleshooting

### Проблема: Application Error / 500

**Причина:** Неправильные переменные окружения

**Решение:**
1. Проверьте логи: `App → web → Runtime Logs`
2. Убедитесь, что все обязательные переменные заданы
3. Проверьте `DATABASE_URL` и `REDIS_URL`

```bash
# В консоли app проверьте подключения:
python backend/manage.py check --deploy
```

### Проблема: Celery не запускается

**Причина:** Неправильный `REDIS_URL`

**Решение:**
```bash
# В логах celery-worker ищите:
[ERROR] Consumer: Cannot connect to redis://...

# Убедитесь, что REDIS_URL корректен:
echo $REDIS_URL
```

### Проблема: Видео не загружаются в B2

**Причина:** Неправильные credentials B2

**Решение:**
```bash
# Проверьте credentials:
python -c "
import boto3
from django.conf import settings
client = boto3.client('s3',
    endpoint_url=settings.BACKBLAZE_CONFIG['ENDPOINT_URL'],
    aws_access_key_id=settings.BACKBLAZE_CONFIG['APPLICATION_KEY_ID'],
    aws_secret_access_key=settings.BACKBLAZE_CONFIG['APPLICATION_KEY']
)
print(client.list_buckets())
"
```

### Проблема: Replicate API timeout

**Причина:** Долгие видео или медленная модель

**Решение:**
```env
# Увеличьте timeout:
REPLICATE_TIMEOUT=600

# Или уменьшите FPS:
FRAME_EXTRACTION_FPS=0.5
```

### Проблема: Email не отправляются

**Причина:** Неправильные SMTP настройки

**Решение:**
```bash
# Тестовая отправка:
python backend/manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
# Должно вернуть 1 (успех)
```

---

## Мониторинг

### Метрики для отслеживания

1. **Затраты на Replicate:**
   - https://replicate.com/account/billing
   - Отслеживайте стоимость инференса

2. **Использование B2:**
   - https://secure.backblaze.com/
   - Хранилище: ~$6/TB
   - Egress (через Cloudflare): $0

3. **App Platform:**
   - DigitalOcean → Apps → Metrics
   - CPU, Memory, Requests

4. **Celery:**
   - Логи: `celery-worker → Runtime Logs`
   - Ищите `[ERROR]` и `[WARNING]`

---

## Масштабирование

### Когда масштабировать:

**CPU > 80%:**
```yaml
# Увеличьте Instance Size или Instance Count
web:
  instance_size: Professional (4GB RAM, 2 vCPU) - $24/mo
  instance_count: 2
```

**Очередь Celery растет:**
```yaml
celery-worker:
  instance_count: 3
  # Или увеличьте concurrency:
  run_command: celery -A compliance_app worker --concurrency=4
```

**Database медленная:**
```yaml
db:
  size: Professional (4GB RAM, 2 vCPU, 40GB SSD) - $50/mo
```

---

## Безопасность

### Чек-лист production:

- [ ] `DEBUG=False`
- [ ] Уникальный `SECRET_KEY` (не из примера!)
- [ ] `ALLOWED_HOSTS` содержит только ваши домены
- [ ] B2 бакет **Private** (не Public)
- [ ] PostgreSQL/Redis используют SSL (`sslmode=require` / `rediss://`)
- [ ] Email использует TLS (`EMAIL_USE_TLS=True`)
- [ ] Настроены HTTPS (SSL certificate от DO автоматически)
- [ ] Backblaze credentials в секретных переменных (не в коде!)
- [ ] Replicate API token в секретных переменных

---

## Дополнительные ресурсы

- [DigitalOcean App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- [Backblaze B2 + Cloudflare Guide](https://www.backblaze.com/docs/cloud-storage-deliver-public-backblaze-b2-content-through-cloudflare-cdn)
- [Replicate Documentation](https://replicate.com/docs)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#tips-and-best-practices)

---

## Поддержка

Если возникли проблемы при деплое:

1. Проверьте логи всех компонентов (web, celery-worker)
2. Убедитесь, что все переменные окружения заданы
3. Проверьте подключение к внешним сервисам (B2, Replicate, Email)
4. Проверьте конфигурацию Dockerfile и команды запуска

**Готово! Ваше приложение должно быть запущено и работать.** 🎉
