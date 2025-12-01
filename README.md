# 🎯 AI-Комплаенс Агент

Система автоматизированного анализа видеоконтента для выявления комплаенс-рисков на основе искусственного интеллекта с верификацией операторами.

## 📋 Описание

AI-Комплаенс Агент - это MVP системы типа "Кентавр" (AI + Оператор) для профессиональных блогеров и видеостудий. Система анализирует видеоконтент с использованием AI-моделей (Whisper, YOLO, NSFW-детекторы) для выявления потенциальных рисков:

- 🔞 NSFW контент и эротика
- 🩸 Жесть, насилие, кровь
- 🤬 Нецензурная лексика
- 📢 Немаркированная реклама
- 🚬 Алкоголь, табак, наркотики
- ⚠️ Запрещенная символика
- 📝 Нарушения 436-ФЗ и 20.3 КоАП

## 🏗️ Архитектура системы

### Обзор компонентов

AI Compliance Agent - это "кентавр" (AI + человек-оператор) система, которая анализирует видеоконтент на предмет комплаенс-рисков. Она сочетает в себе Django монолит, Django REST Framework (DRF) API, HTMX-веб-интерфейс, Celery workers, Redis, PostgreSQL, хранилище Backblaze B2 с Cloudflare CDN и AI-модели на Replicate.

Ключевые характеристики:

- **Django 5 приложение** с модульными настройками (`backend/compliance_app/settings/`)
- **REST API** через DRF с JWT-аутентификацией
- **HTMX Frontend** для клиентских dashboards и консолей операторов
- **Celery Workers & Beat** для оркестрации AI-обработки и периодических задач
- **Redis** для брокера Celery, кэширования signed URLs и координации фоновых задач
- **PostgreSQL** как основная система хранения (проекты, видео, триггеры, метки, метаданные pipeline)
- **Backblaze B2 + Cloudflare** для надежного хранения объектов и CDN-дистрибуции
- **Replicate** для GPU-инференса AI (Whisper, YOLO, NSFW/Violence детекторы, OCR)

### Технологический стек

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Backend** | Python 3.11, Django 5 | Основное приложение |
| **Frontend** | Django Templates, HTMX, Bootstrap 5 | Веб-интерфейс |
| **Task Queue** | Celery + Redis | Фоновая обработка |
| **Database** | PostgreSQL (jsonb для AI отчетов) | Основное хранилище |
| **Storage** | Backblaze B2 + Cloudflare CDN | Файлы и CDN |
| **AI Inference** | Replicate (Serverless GPU) | AI-модели |

### AI Модели

| Модель | Назначение |
|--------|------------|
| OpenAI Whisper (small) | Распознавание речи (ASR) |
| YOLOv8s | Детекция объектов |
| Falconsai NSFW | Детекция 18+ контента |
| ViT Violence | Детекция жести/насилия |
| EasyOCR | Распознавание текста |

### Структура проекта

```
ai-compliance-agent/
├── docs/                       # 📚 Документация
│   └── LOCAL_DEVELOPMENT.md   # Руководство по локальной разработке
├── backend/                    # Django приложение
│   ├── compliance_app/         # Основные настройки
│   │   ├── settings/           # Модульные настройки Django
│   │   │   ├── __init__.py     # Автоматический выбор окружения
│   │   │   ├── base.py         # Общие настройки
│   │   │   ├── dev.py          # Настройки разработки
│   │   │   └── prod.py         # Настройки production
│   │   └── config_validator.py # Валидатор конфигурации
│   ├── users/                  # Управление пользователями (Client/Operator/Admin)
│   ├── projects/               # Проекты и видео
│   ├── ai_pipeline/            # AI обработка (Celery tasks, AI services)
│   ├── operators/              # Рабочий стол оператора
│   ├── admins/                 # Админ-панель
│   └── storage/                # Интеграция с B2/Cloudflare
├── scripts/                    # Вспомогательные скрипты
│   └── entrypoint.sh           # Docker entrypoint для миграций и collectstatic
├── celery-worker/              # Скрипты Celery worker
├── .env.example                # Пример конфигурации для production
├── .env.docker                 # Пример конфигурации для Docker Compose
├── Dockerfile                  # Multi-stage Docker образ
├── docker-compose.yml          # Docker Compose для локальной разработки
├── requirements.txt            # Python зависимости (pinned versions)
├── requirements.dev.txt        # Зависимости для разработки
└── README.md                   # Этот файл
```

## 🚀 Быстрый старт

### 📖 Полное руководство по настройке

**Новичкам рекомендуется начать с полного руководства по локальной разработке:**

**[📚 docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)** - исчерпывающее руководство по настройке окружения, запуску проекта и решению проблем.

Если у вас уже есть опыт, ниже приведены краткие шаги для быстрого старта.

### Требования

Перед началом разработки убедитесь, что у вас установлено:

- **Python 3.11+** - проверьте: `python --version`
- **PostgreSQL** (если не используете Docker) - `postgres --version`
- **Redis** (если не используете Docker) - `redis-cli --version`
- **Docker & Docker Compose** (для контейнерной разработки):
  - Установите Docker: https://docs.docker.com/get-docker/
  - Проверьте: `docker --version` и `docker compose --version`
- **Git** - `git --version`
- **curl** или **wget** - для тестирования API endpoints

#### Установка системных пакетов

**macOS с Homebrew:**
```bash
brew install python@3.11 postgresql redis docker-desktop
```

**Ubuntu/Debian:**
```bash
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
  postgresql-client redis-tools docker.io docker-compose
```

**Fedora/RHEL:**
```bash
sudo dnf install -y python3.11 python3.11-devel postgresql-libs redis docker docker-compose
```

### 1. Настройка конфигурации

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Или используйте скрипт
./setup_env.sh

# Откройте .env и заполните обязательные переменные
nano .env
```

**Обязательные переменные:**
- `SECRET_KEY` - секретный ключ Django
- `DATABASE_URL` - подключение к PostgreSQL
- `REDIS_URL` - подключение к Redis
- `REPLICATE_API_TOKEN` - токен Replicate API
- `BACKBLAZE_*` - credentials Backblaze B2

### 2. Выберите окружение (DJANGO_ENV)

Отредактируйте `.env` и установите:

```bash
# Для локальной разработки (проще всего)
DJANGO_ENV=development

# Для production-like тестирования (с проверками безопасности)
DJANGO_ENV=production
```

**Различия:**
- `development`: DEBUG=True, SQLite по умолчанию, email в консоль, без HTTPS redirect
- `production`: DEBUG=False, PostgreSQL требуется, SMTP требуется, строгая безопасность

### 3. Локальная разработка

**Вариант A: С использованием Docker Compose (рекомендуется)**

```bash
# Скопируйте конфигурацию Docker
cp .env.docker .env

# Запустите все сервисы
docker compose up -d

# Выполните миграции
docker compose exec web python manage.py migrate

# Создайте суперпользователя
docker compose exec web python manage.py createsuperuser

# Просмотр логов
docker compose logs -f web

# Остановка сервисов
docker compose down
```

**Вариант B: Локальная разработка без Docker**

```bash
# Создайте виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt -r requirements.dev.txt

# Настройте окружение для разработки
export DJANGO_ENV=development
export DATABASE_URL=sqlite:///db.sqlite3

# Запустите Redis (обязательно)
redis-server

# Запустите миграции
cd backend
python manage.py migrate

# Создайте суперпользователя
python manage.py createsuperuser

# Соберите статику
python manage.py collectstatic --noinput

# Запустите сервер разработки
python manage.py runserver

# В отдельном терминале запустите Celery
celery -A compliance_app worker --loglevel=info
```

### 4. Проверка конфигурации

```bash
python backend/compliance_app/config_validator.py
```

Ожидаемый вывод:
```
✅ Configuration is valid! All variables are set correctly.
```

## 📚 Разработка

### 📖 Подробное руководство

**Для полного руководства по разработке см.: [📚 docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)**

Это руководство включает:
- Подробную настройку окружения
- Docker и нативную разработку
- Тестирование и отладку
- Troubleshooting и советы

### Полезные команды (Makefile)

```bash
# Просмотр всех доступных команд
make help

# Docker разработка
make docker-up           # Запустить все сервисы
make docker-migrate      # Выполнить миграции
make docker-logs         # Просмотр логов
make docker-down         # Остановить сервисы

# Локальная разработка
make install            # Установить зависимости
make migrate            # Выполнить миграции
make test               # Запустить тесты
make lint               # Проверить код
```

### Создание миграций

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

### Запуск тестов

```bash
# Django test runner
cd backend
python manage.py test

# С pytest (если установлен)
pytest --cov=. --cov-report=html --cov-report=term
```

### Линтинг и форматирование

```bash
flake8 backend/
black backend/
isort backend/
```

### Отладка

**Django shell:**
```bash
cd backend
python manage.py shell
```

**Проверка настроек:**
```bash
python manage.py check --deploy
```

## ⚙️ Конфигурация

### Модульная архитектура настроек

Приложение использует модульную структуру настроек для поддержки разных окружений:

```
backend/compliance_app/settings/
├── __init__.py      # Автоматический выбор окружения на основе DJANGO_ENV
├── base.py          # Общие настройки для всех окружений
├── dev.py           # Настройки разработки (DEBUG=True, ослабленная безопасность)
└── prod.py          # Настройки production (строгая валидация, безопасность)
```

### Переменные окружения по доменам

#### Django Core

| Переменная | Описание | Обязательно | По умолчанию |
|------------|----------|------------|-------------|
| `DJANGO_ENV` | Выбор окружения (`development` или `production`) | Нет | `production` |
| `SECRET_KEY` | Секретный ключ Django для криптографической подписи | Да | `unsafe-secret-key` |
| `DEBUG` | Режим отладки | Нет | `False` |
| `ALLOWED_HOSTS` | Разрешенные хосты через запятую | Нет | `[]` |

#### База данных

| Переменная | Описание | Обязательно | Dev | Prod |
|------------|----------|------------|-----|------|
| `DATABASE_URL` | URL подключения к базе данных | Да | SQLite по умолчанию | PostgreSQL обязателен |

#### Redis

| Переменная | Описание | Обязательно |
|------------|----------|------------|
| `REDIS_URL` | URL подключения к Redis | Да |

#### Хранилище / Backblaze B2

| Переменная | Описание | Обязательно |
|------------|----------|------------|
| `BACKBLAZE_ENDPOINT_URL` | Endpoint URL B2 | Да |
| `BACKBLAZE_APPLICATION_KEY_ID` | Application Key ID | Да |
| `BACKBLAZE_APPLICATION_KEY` | Application Key | Да |
| `BACKBLAZE_BUCKET_NAME` | Имя бакета | Да |

#### Replicate AI Services

| Переменная | Описание | Обязательно | Dev | Prod |
|------------|----------|------------|-----|------|
| `REPLICATE_API_TOKEN` | API токен Replicate | Нет | Опционально | Обязательно |

#### Email

| Переменная | Описание | Обязательно | Dev | Prod |
|------------|----------|------------|-----|------|
| `EMAIL_HOST` | SMTP хост | Нет | Консоль | Обязательно |
| `EMAIL_PORT` | SMTP порт | Нет | Консоль | Обязательно |
| `EMAIL_HOST_USER` | SMTP пользователь | Нет | Консоль | Обязательно |
| `EMAIL_HOST_PASSWORD` | SMTP пароль | Нет | Консоль | Обязательно |

#### Cloudflare / CDN

| Переменная | Описание | Обязательно |
|------------|----------|------------|
| `CLOUDFLARE_ZONE_ID` | Zone ID Cloudflare | Нет |
| `CLOUDFLARE_API_TOKEN` | API токен Cloudflare | Нет |

#### AI Pipeline

| Переменная | Описание | Обязательно | По умолчанию |
|------------|----------|------------|-------------|
| `ALLOWED_VIDEO_FORMATS` | Разрешенные форматы видео | Нет | `mp4,avi,mov,mkv,webm` |
| `MAX_VIDEO_FILE_SIZE` | Макс. размер видео (байты) | Нет | `2147483648` (2GB) |
| `MAX_VIDEO_DURATION` | Макс. длительность видео (сек) | Нет | `3600` (1 час) |

#### Celery

| Переменная | Описание | Обязательно | По умолчанию |
|------------|----------|------------|-------------|
| `CELERY_BROKER_URL` | URL брокера Celery | Нет | `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | URL для результатов | Нет | `REDIS_URL` |

#### Настройки B2 и Retry

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `B2_MAX_RETRIES` | Макс. количество попыток B2 | `3` |
| `B2_RETRY_BACKOFF` | Initial backoff в секундах | `1` |
| `B2_RETRY_BACKOFF_MAX` | Макс. backoff в секундах | `60` |

### Примеры конфигурации

#### Минимальная конфигурация для разработки

```bash
# .env файл (development mode)
DJANGO_ENV=development
DEBUG=True
SECRET_KEY=your-development-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Тестовые токены (не будут вызывать реальные сервисы)
REPLICATE_API_TOKEN=test_token_123
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=test_key_id
BACKBLAZE_APPLICATION_KEY=test_key
BACKBLAZE_BUCKET_NAME=test-bucket
```

#### Production конфигурация

```bash
# .env файл (production mode)
DJANGO_ENV=production
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:password@host:5432/dbname
REDIS_URL=redis://user:password@host:6379/0

# Email настройки
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Backblaze B2
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=your-key-id
BACKBLAZE_APPLICATION_KEY=your-secret-key
BACKBLAZE_BUCKET_NAME=your-bucket

# Replicate AI
REPLICATE_API_TOKEN=r8_your-replicate-token

# Cloudflare CDN (опционально)
CLOUDFLARE_ZONE_ID=your-zone-id
CLOUDFLARE_API_TOKEN=your-cloudflare-token

# Дашборд URL для уведомлений
DASHBOARD_URL=https://yourdomain.com/client/dashboard/
```

## 📡 API документация

### Обзор

Система предоставляет два complementary интерфейса:

- **REST API** (`/api/*`) - JSON ответы для программного доступа
  - JWT токен-аутентификация
  - Подходит для внешних интеграций, мобильных приложений, автоматизации
  
- **HTMX Interface** (`/client/*`) - Server-rendered HTML partials
  - Django session аутентификация
  - Оптимизирован для веб-браузерных взаимодействий с минимальным JavaScript
  - CSRF защита включена

### Аутентификация

#### JWT Аутентификация (REST API)

**Получение токена:**
```http
POST /api/auth/token/
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "your_password"
}
```

**Ответ:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Обновление токена:**
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Время жизни токенов:**
- Access token: 1 час
- Refresh token: 7 дней

**Использование:**
Включайте access токен в заголовке `Authorization` для всех API запросов:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### Session Аутентификация (HTMX)

Стандартная Django session-based аутентификация:
- Login: `POST /client/users/login/`
- Logout: `POST /client/users/logout/`
- CSRF токен требуется для всех POST/PUT/DELETE запросов
- Session cookie автоматически управляется браузером

### Base URLs

| Окружение | Base URL | Описание |
|-----------|----------|----------|
| Локальное | `http://localhost:8000` | Разработка |
| Production | `https://yourdomain.com` | Продакшн |

### API Ресурсы

| Ресурс | Эндпоинт | Методы | Описание |
|--------|----------|--------|----------|
| **Projects** | `/api/projects/` | GET, POST, PUT, DELETE | Управление проектами |
| **Videos** | `/api/videos/` | GET, POST, PUT, DELETE | Загрузка и управление видео |
| **AITriggers** | `/api/triggers/` | GET, POST, PUT, DELETE | AI триггеры и правила |
| **VerificationTasks** | `/api/verification-tasks/` | GET, POST, PUT, DELETE | Задачи верификации операторов |
| **OperatorLabels** | `/api/operator-labels/` | GET, POST, PUT, DELETE | Метки операторов |
| **PipelineExecutions** | `/api/pipeline-executions/` | GET, POST, PUT, DELETE | Статусы обработки pipeline |
| **RiskDefinitions** | `/api/risk-definitions/` | GET, POST, PUT, DELETE | Определения рисков |
| **Users** | `/api/users/` | GET, PUT, PATCH | Управление пользователями |
| **Auth** | `/api/auth/token/` | POST | JWT аутентификация |

### Примеры запросов

#### Создание проекта

```http
POST /api/projects/
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "name": "My Video Project",
  "description": "Test project for compliance checking"
}
```

**Ответ:**
```json
{
  "id": 1,
  "name": "My Video Project",
  "description": "Test project for compliance checking",
  "owner": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Загрузка видео

```http
POST /api/videos/
Authorization: Bearer your-access-token
Content-Type: multipart/form-data

project_id=1
file=@/path/to/video.mp4
title=Test Video
description=Test video for compliance
```

**Ответ:**
```json
{
  "id": 1,
  "title": "Test Video",
  "description": "Test video for compliance",
  "project": 1,
  "file": "/media/videos/test_video.mp4",
  "file_size": 52428800,
  "duration": 300,
  "checksum": "sha256:abc123...",
  "status": "uploaded",
  "created_at": "2024-01-15T10:35:00Z"
}
```

#### Получение списка проектов

```http
GET /api/projects/
Authorization: Bearer your-access-token
```

**Ответ:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "My Video Project",
      "description": "Test project for compliance checking",
      "owner": 1,
      "video_count": 3,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### HTMX Interface

HTMX интерфейс использует те же эндпоинты но с префиксом `/client/` и возвращает HTML partials вместо JSON.

#### Основные HTMX эндпоинты

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/client/dashboard/` | GET | Главный дашборд |
| `/client/projects/` | GET, POST | Список и создание проектов |
| `/client/projects/{id}/` | GET, PUT, DELETE | Детали проекта |
| `/client/videos/upload/` | GET, POST | Загрузка видео |
| `/client/reports/{id}/` | GET | Детали отчета |

### Статусы и коды ошибок

| Код | Описание |
|-----|----------|
| 200 | OK - успешный запрос |
| 201 | Created - ресурс создан |
| 400 | Bad Request - ошибка валидации |
| 401 | Unauthorized - требуется аутентификация |
| 403 | Forbidden - недостаточно прав |
| 404 | Not Found - ресурс не найден |
| 429 | Too Many Requests - превышен лимит |
| 500 | Internal Server Error - ошибка сервера |

### Пагинация

Все list эндпоинты поддерживают пагинацию:

```http
GET /api/projects/?page=2&page_size=10
```

**Ответ:**
```json
{
  "count": 25,
  "next": "http://localhost:8000/api/projects/?page=3",
  "previous": "http://localhost:8000/api/projects/?page=1",
  "results": [...]
}
```

### Загрузка файлов

Видео загружаются через `multipart/form-data`:

```http
POST /api/videos/
Authorization: Bearer your-access-token
Content-Type: multipart/form-data

project_id=1
file=@video.mp4
title=My Video
description=Description
```

**Ограничения:**
- Макс. размер: 2GB
- Форматы: mp4, avi, mov, mkv, webm
- Макс. длительность: 1 час

### Инструменты документации API

- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

## 🚀 Production Deployment

### Подготовка к деплою

#### 1. Требования к окружению

- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Docker (опционально)
- Backblaze B2 аккаунт
- Replicate API токен

#### 2. Настройка переменных окружения

Создайте production `.env` файл:

```bash
# Базовые настройки
DJANGO_ENV=production
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# База данных PostgreSQL
DATABASE_URL=postgres://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://user:password@host:6379/0

# Email настройки
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Backblaze B2
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=your-key-id
BACKBLAZE_APPLICATION_KEY=your-secret-key
BACKBLAZE_BUCKET_NAME=your-bucket

# Replicate AI
REPLICATE_API_TOKEN=r8_your-replicate-token

# Cloudflare CDN (опционально)
CLOUDFLARE_ZONE_ID=your-zone-id
CLOUDFLARE_API_TOKEN=your-cloudflare-token

# Дашборд URL для уведомлений
DASHBOARD_URL=https://yourdomain.com/client/dashboard/
```

#### 3. Валидация конфигурации

```bash
python backend/compliance_app/config_validator.py
```

### Деплой на DigitalOcean App Platform

#### 1. Подготовка репозитория

Убедитесь что в репозитории есть:
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `requirements.txt` с pinned версиями

#### 2. Создание приложения

1. Зайдите в DigitalOcean Control Panel
2. Создайте новое App Platform приложение
3. Подключите ваш репозиторий
4. Настройте переменные окружения из раздела выше

#### 3. Конфигурация компонентов

**Web Service:**
- Build Command: `cd backend && python manage.py collectstatic --noinput`
- Run Command: `cd backend && gunicorn compliance_app.wsgi:application --bind 0.0.0.0:$PORT`
- Instance Size: 1GB RAM (минимум)
- HTTP Port: 8000

**Worker Service (Celery):**
- Run Command: `cd backend && celery -A compliance_app worker --loglevel=info`
- Instance Size: 1GB RAM (минимум)

**Database:**
- PostgreSQL 1GB RAM
- Создайте базу данных и скопируйте connection string

**Redis:**
- Redis 1GB RAM
- Скопируйте connection string

#### 4. Настройка хранилища

**Backblaze B2:**
1. Создайте аккаунт на https://www.backblaze.com/b2/sign-up.html
2. Создайте Private бакет
3. Создайте Application Key с правами на запись
4. Добавьте credentials в переменные окружения

**Cloudflare CDN (опционально):**
1. Добавьте домен в Cloudflare
2. Настройте CNAME для CDN
3. Создайте API токен с Zone:Edit правами
4. Добавьте Zone ID и токен в переменные окружения

#### 5. Запуск деплоя

1. Commit и push изменений в репозиторий
2. DigitalOcean автоматически запустит деплой
3. Следите за логами в DigitalOcean dashboard

#### 6. Пост-деплой настройки

**Выполните миграции:**
```bash
# Через DigitalOcean console или SSH
doctl apps exec YOUR_APP_ID --command "cd backend && python manage.py migrate"
```

**Создайте суперпользователя:**
```bash
doctl apps exec YOUR_APP_ID --command "cd backend && python manage.py createsuperuser"
```

**Проверьте работоспособность:**
- Откройте https://yourdomain.com
- Проверьте /admin/ панель
- Протестируйте загрузку видео

### Docker Deployment

#### 1. Сборка образа

```bash
docker build -t ai-compliance-agent .
```

#### 2. Запуск с Docker Compose

```bash
# Production compose файл
docker-compose -f docker-compose.prod.yml up -d
```

#### 3. Пример docker-compose.prod.yml

```yaml
version: '3.8'

services:
  web:
    image: ai-compliance-agent:latest
    command: gunicorn compliance_app.wsgi:application --bind 0.0.0.0:8000
    ports:
      - "8000:8000"
    environment:
      - DJANGO_ENV=production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis

  worker:
    image: ai-compliance-agent:latest
    command: celery -A compliance_app worker --loglevel=info
    environment:
      - DJANGO_ENV=production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis

  beat:
    image: ai-compliance-agent:latest
    command: celery -A compliance_app beat --loglevel=info
    environment:
      - DJANGO_ENV=production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ai_compliance_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}

volumes:
  postgres_data:
```

### Мониторинг и логирование

#### Логи DigitalOcean

```bash
# Логи web сервиса
doctl apps logs YOUR_APP_ID --type run

# Логи worker
doctl apps logs YOUR_APP_ID --type worker

# Логи всех компонентов
doctl apps logs YOUR_APP_ID
```

#### Логи Docker

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f web
docker compose logs -f worker
```

#### Мониторинг метрик

- **DigitalOcean App Platform**: Built-in metrics dashboard
- **Backblaze B2**: https://secure.backblaze.com/b2_buckets.htm
- **Replicate**: https://replicate.com/account/billing
- **Cloudflare**: Analytics dashboard

## 🔧 Troubleshooting

### Частые проблемы

#### 1. Ошибка: "REPLICATE_API_TOKEN must be set"

```bash
# Проверьте .env файл
cat .env | grep REPLICATE_API_TOKEN

# Проверьте конфигурацию
python backend/compliance_app/config_validator.py
```

#### 2. Ошибка: "Cannot connect to database"

```bash
# Проверьте DATABASE_URL
echo $DATABASE_URL

# Проверьте подключение
cd backend
python manage.py dbshell
```

#### 3. Ошибка: "Redis connection refused"

```bash
# Проверьте Redis
redis-cli ping
# Должно ответить: PONG

# Проверьте REDIS_URL
echo $REDIS_URL
```

#### 4. Проблемы с загрузкой файлов

```bash
# Проверьте B2 credentials
python -c "
import os
from backend.storage.b2_utils import B2Utils
b2 = B2Utils()
print('B2 connection:', b2.test_connection())
"
```

#### 5. Ошибки миграций

```bash
# Проверьте статус миграций
python manage.py showmigrations

# Принудительно примените миграции
python manage.py migrate --fake-initial

# Откатите миграцию если нужно
python manage.py migrate app_name migration_name
```

### Отладка в development

#### Django debug toolbar

```bash
pip install django-debug-toolbar
# Добавьте 'debug_toolbar' в INSTALLED_APPS
# Добавьте в MIDDLEWARE
```

#### SQL логирование

```python
# settings/dev.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

#### Отладка Celery

```bash
# Проверьте статус Celery
celery -A compliance_app inspect active

# Проверьте очереди
celery -A compliance_app inspect reserved

# Мониторинг
celery -A compliance_app events
```

### Production проблемы

#### High memory usage

1. Увеличте размер инстанса
2. Настройте `CELERY_WORKER_CONCURRENCY`
3. Используйте `CELERY_WORKER_MAX_TASKS_PER_CHILD`

#### Slow response times

1. Проверьте `django-debug-toolbar` для медленных запросов
2. Оптимизируйте запросы к БД (select_related, prefetch_related)
3. Настройте Redis кэширование

#### File upload issues

1. Проверьте лимиты размера файлов в nginx/web сервере
2. Убедитесь что B2 бакет имеет достаточно места
3. Проверьте сетевое соединение с B2

### Health checks

#### Django health check

```bash
python manage.py check --deploy
```

#### Custom health check endpoint

```http
GET /api/health/
```

**Ответ:**
```json
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "b2": "ok",
  "replicate": "ok"
}
```

## 💰 Оценка затрат (MVP)

### DigitalOcean App Platform

| Сервис | Цена/мес | Описание |
|--------|----------|----------|
| Web Service (1GB RAM) | $12 | Django приложение |
| Celery Worker (1GB RAM) | $12 | Фоновая обработка |
| PostgreSQL (1GB RAM) | $12 | База данных |
| Redis (1GB RAM) | $15 | Кэш и брокер |
| **Итого:** | **~$51/мес** | |

### Внешние сервисы

| Сервис | Цена | Описание |
|--------|------|----------|
| **Backblaze B2** | $6/TB/мес | Хранилище |
| **Replicate** | ~$0.0002/сек | GPU инференс |
| **Cloudflare CDN** | $0 | Бесплатный egress с B2 |

**Пример:** Обработка 100 видео по 10 минут = ~$10-15/мес (Replicate)

## 🔑 Получение API ключей

### Backblaze B2

1. Зарегистрируйтесь: https://www.backblaze.com/b2/sign-up.html
2. Создайте бакет (Private)
3. Создайте Application Key
4. Скопируйте credentials в `.env`

### Replicate

1. Зарегистрируйтесь: https://replicate.com
2. Создайте API токен: https://replicate.com/account/api-tokens
3. Скопируйте токен (начинается с `r8_`) в `.env`

### Cloudflare (опционально)

1. Зарегистрируйтесь: https://cloudflare.com
2. Добавьте домен
3. Настройте CNAME для CDN
4. Создайте API токен
5. Скопируйте Zone ID и токен в `.env`

## 🔒 Безопасность

- ✅ Все чувствительные данные в переменных окружения
- ✅ `.env` файл в `.gitignore`
- ✅ Валидация конфигурации при запуске
- ✅ B2 бакеты приватные (signed URLs)
- ✅ PostgreSQL/Redis с SSL в production
- ✅ Django security middleware включен

## 🤝 Поддержка

### Статус проекта

✅ MVP v1.0 - Готов к деплою
- Полная конфигурация через environment variables
- Автоматическая валидация при запуске
- Документация по деплою
- Интеграция с B2, Replicate, Cloudflare

### Следующие этапы (v2.0)

- [ ] Автоматический биллинг (Stripe)
- [ ] Обучение custom YOLOv8 на собранных данных
- [ ] Faster-Whisper для ускорения ASR
- [ ] Автоматическая очередь задач для операторов
- [ ] Плагины для Adobe Premiere / DaVinci Resolve
- [ ] Mobile-responsive operator workbench

---

## 📝 Лицензия

Proprietary - All rights reserved

---

**Готово к деплою! 🎉**

Начните с настройки переменных окружения, затем следуйте инструкциям по деплою.