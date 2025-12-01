# Руководство по локальной разработке

Это руководство поможет вам настроить окружение для разработки AI-Комплаенс Агента на вашей локальной машине. Следуйте шагам последовательно, чтобы избежать проблем.

## 📋 Содержание

- [Требования](#-требования)
- [Настройка окружения](#-настройка-окружения)
- [Запуск с Docker Compose (рекомендуется)](#-запуск-с-docker-compose-рекомендуется)
- [Запуск без Docker (нативная разработка)](#-запуск-без-docker-нативная-разработка)
- [Работа с Celery](#-работа-с-celery)
- [Тестирование](#-тестирование)
- [Линтинг и форматирование](#-линтинг-и-форматирование)
- [Доступ к интерфейсам](#-доступ-к-интерфейсам)
- [Полезные команды](#-полезные-commands)
- [Troubleshooting](#-troubleshooting)
- [Загрузка тестовых данных](#-загрузка-тестовых-данных)

## 🎯 Требования

### Обязательные компоненты

- **Python 3.11+**
  ```bash
  # Проверка версии
  python --version
  # Должно быть 3.11.x или выше
  ```

- **Git**
  ```bash
  git --version
  ```

- **Docker & Docker Compose** (для контейнерной разработки)
  ```bash
  docker --version
  docker compose --version
  ```

### Системные зависимости

#### macOS (Homebrew)
```bash
brew install python@3.11 docker-desktop postgresql redis ffmpeg
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
  postgresql-client redis-tools ffmpeg docker.io docker-compose
```

#### Fedora/RHEL/CentOS
```bash
sudo dnf install -y python3.11 python3.11-devel postgresql-libs redis ffmpeg docker docker-compose
```

#### Windows (WSL2)
```bash
# В WSL2 Ubuntu
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
  postgresql-client redis-tools ffmpeg
# Docker Desktop установить отдельно в Windows
```

### Проверка ffmpeg

FFmpeg обязателен для обработки видео:
```bash
ffmpeg -version
# Должна отобразиться версия ffmpeg
```

## 🔧 Настройка окружения

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd ai-compliance-agent
```

### 2. Создание конфигурации

Используйте автоматический скрипт:
```bash
./setup_env.sh
```

Или создайте вручную:
```bash
cp .env.example .env
```

### 3. Редактирование .env файла

Откройте `.env` и установите следующие переменные:

```bash
# Выбор окружения (обязательно для локальной разработки)
DJANGO_ENV=development

# Базовые настройки
SECRET_KEY=your-secret-key-here-generate-with-django
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# База данных (SQLite для быстрой разработки)
DATABASE_URL=sqlite:///db.sqlite3

# Redis (обязательно)
REDIS_URL=redis://localhost:6379/0

# Email для разработки (в консоль)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Тестовые токены (для разработки без реальных сервисов)
REPLICATE_API_TOKEN=test_token_123
BACKBLAZE_ENDPOINT_URL=http://localhost:9000
BACKBLAZE_APPLICATION_KEY_ID=minioadmin
BACKBLAZE_APPLICATION_KEY=minioadmin
BACKBLAZE_BUCKET_NAME=ai-compliance-videos
```

### 4. Генерация SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Проверка конфигурации

```bash
python backend/compliance_app/config_validator.py
```

Ожидаемый вывод:
```
✅ Configuration is valid! All variables are set correctly.
```

## 🐳 Запуск с Docker Compose (рекомендуется)

Этот способ проще всего начать, так как все сервисы уже настроены.

### 1. Используйте Docker конфигурацию

```bash
cp .env.docker .env
```

### 2. Запуск всех сервисов

```bash
docker compose up -d
```

Это запустит:
- **PostgreSQL** (порт 5432)
- **Redis** (порт 6379) 
- **MinIO** (S3-совместимое хранилище, порты 9000/9001)
- **Web** (Django, порт 8000)
- **Celery Worker** (обработка AI pipeline)
- **Celery Beat** (периодические задачи)

### 3. Ожидание запуска сервисов

```bash
# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### 4. Выполнение миграций

```bash
docker compose exec web python manage.py migrate
```

### 5. Создание суперпользователя

```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Доступ к сервисам

- **Веб-приложение**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **PostgreSQL**: localhost:5432 (postgres/postgres)
- **Redis**: localhost:6379

### 7. Полезные Docker команды

```bash
# Просмотр логов конкретного сервиса
docker compose logs -f web
docker compose logs -f celery-worker

# Перезапуск сервиса
docker compose restart web

# Остановка всех сервисов
docker compose down

# Очистка с удалением данных
docker compose down -v

# Shell в веб-контейнере
docker compose exec web bash

# Выполнение Django команд
docker compose exec web python manage.py shell
```

## 💻 Запуск без Docker (нативная разработка)

Этот способ подходит для опытных разработчиков, предпочитающих нативную среду.

### 1. Создание виртуального окружения

```bash
python3.11 -m venv venv

# Активация (Linux/macOS)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt -r requirements.dev.txt
```

### 3. Настройка окружения

```bash
export DJANGO_ENV=development
export DATABASE_URL=sqlite:///db.sqlite3
export REDIS_URL=redis://localhost:6379/0
```

### 4. Запуск Redis (обязательно)

```bash
# В отдельном терминале
redis-server
```

### 5. Выполнение миграций

```bash
cd backend
python manage.py migrate
```

### 6. Создание суперпользователя

```bash
python manage.py createsuperuser
```

### 7. Сбор статики

```bash
python manage.py collectstatic --noinput
```

### 8. Запуск веб-сервера

```bash
python manage.py runserver
```

## 🔄 Работа с Celery

### В Docker (автоматически)

Celery worker и beat запускаются автоматически с docker compose.

### Без Docker (ручной запуск)

#### Celery Worker

```bash
# В отдельном терминале
cd backend
celery -A compliance_app worker --loglevel=info
```

#### Celery Beat (периодические задачи)

```bash
# В третьем терминале
cd backend
celery -A compliance_app beat --loglevel=info
```

#### Проверка статуса Celery

```bash
# Проверка активных задач
celery -A compliance_app inspect active

# Проверка зарегистрированных задач
celery -A compliance_app inspect registered
```

### Использование Makefile для Celery

```bash
# Запуск worker
make celery-worker

# Запуск beat
make celery-beat

# Проверка статуса
make celery-status
```

## 🧪 Тестирование

### Запуск тестов Django

```bash
cd backend
python manage.py test
```

### Запуск с pytest (рекомендуется)

```bash
cd backend
pytest --cov=. --cov-report=html --cov-report=term
```

### Запуск тестов в Docker

```bash
docker compose exec web python manage.py test
```

### Использование Makefile

```bash
make test              # Django test runner
make test-coverage     # pytest с coverage
```

### Тестирование конкретных модулей

```bash
# Django
python manage.py test projects.tests

# pytest
pytest projects/tests/test_api.py -v
```

## 🎨 Линтинг и форматирование

### Проверка кода

```bash
# Flake8 линтинг
flake8 backend/

# Django system checks
python manage.py check --deploy
```

### Форматирование кода

```bash
# Black форматирование
black backend/

# isort сортировка импортов
isort backend/
```

### Использование Makefile

```bash
make lint              # Проверить код
make format            # Отформатировать код
make check             # Django system checks
```

### Автоматическое форматирование

```bash
# Все вместе
make format && make lint
```

## 🌐 Доступ к интерфейсам

После запуска приложения доступны следующие интерфейсы:

### Основные интерфейсы

- **HTMX Dashboard**: http://localhost:8000/client/dashboard/
  - Основной интерфейс для клиентов
  - Управление проектами и видео
  
- **Operator Dashboard**: http://localhost:8000/operators/dashboard/
  - Рабочее место оператора верификации
  
- **Admin панель**: http://localhost:8000/admin/
  - Административная панель Django
  - Управление всеми моделями данных

### API документация

- **Swagger UI**: http://localhost:8000/api/docs/
  - Интерактивная документация API
  - Тестирование эндпоинтов
  
- **ReDoc**: http://localhost:8000/api/redoc/
  - Альтернативная документация API
  
- **OpenAPI Schema**: http://localhost:8000/api/schema/
  - JSON схема API

### Хранилище (только в Docker)

- **MinIO Console**: http://localhost:9001
  - Логин: `minioadmin`
  - Пароль: `minioadmin`
  - Управление файлами и бакетами

## 🛠️ Полезные команды

### Работа с базой данных

```bash
# Создание миграций
python manage.py makemigrations

# Применение миграций
python manage.py migrate

# Проверка статуса миграций
python manage.py showmigrations

# Django shell
python manage.py shell

# Резервное копирование (Docker)
docker compose exec postgres pg_dump -U postgres ai_compliance_db > backup.sql
```

### Управление пользователями

```bash
# Создание суперпользователя
python manage.py createsuperuser

# Изменение пароля
python manage.py changepassword username
```

### Очистка

```bash
# Очистка Python cache
make clean

# Очистка Docker volumes
make clean-docker

# Ручная очистка
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## 🔧 Troubleshooting

### Проблемы с Docker

#### Docker permission denied
```bash
# Добавление пользователя в docker group
sudo usermod -aG docker $USER
# Перезайдите в систему или выполните:
newgrp docker
```

#### Порты уже заняты
```bash
# Проверка занятых портов
netstat -tulpn | grep :8000
netstat -tulpn | grep :5432

# Изменение портов в docker-compose.yml
ports:
  - "8001:8000"  # Использовать другой порт
```

### Проблемы с зависимостями

#### Python не найден
```bash
# Убедитесь что используется Python 3.11+
which python
python --version

# Если несколько версий Python
python3.11 --version
```

#### Ошибки при установке пакетов
```bash
# Обновление pip
pip install --upgrade pip

# Установка с флагом --no-cache-dir
pip install --no-cache-dir -r requirements.txt
```

### Проблемы с ffmpeg

#### FFmpeg не найден
```bash
# Проверка установки
ffmpeg -version

# Установка (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Установка (macOS)
brew install ffmpeg
```

### Проблемы с базой данных

#### SQLite permission denied
```bash
# Проверка прав на директорию
ls -la backend/
chmod 755 backend/
```

#### PostgreSQL connection refused
```bash
# Проверка запущен ли PostgreSQL
docker compose ps postgres

# Проверка логов
docker compose logs postgres

# Рестарт PostgreSQL
docker compose restart postgres
```

### Проблемы с Redis

#### Redis connection refused
```bash
# Проверка Redis
redis-cli ping
# Должно ответить: PONG

# Проверка в Docker
docker compose exec redis redis-cli ping
```

### Проблемы с миграциями

#### Migration conflicts
```bash
# Показать статус миграций
python manage.py showmigrations

# Откатить миграцию
python manage.py migrate app_name migration_name

# Принудительно применить миграции
python manage.py migrate --fake-initial
```

### Проблемы с Celery

#### Worker не запускается
```bash
# Проверка подключения к Redis
redis-cli ping

# Проверка конфигурации
celery -A compliance_app inspect ping

# Рестарт worker (Docker)
docker compose restart celery-worker
```

## 📊 Загрузка тестовых данных

### Создание тестовых данных через Django shell

```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from projects.models import Project

User = get_user_model()

# Создание тестового клиента
client = User.objects.create_user(
    username='testclient',
    email='client@example.com',
    password='testpass123',
    user_type='client'
)

# Создание тестового оператора
operator = User.objects.create_user(
    username='testoperator',
    email='operator@example.com',
    password='testpass123',
    user_type='operator'
)

# Создание тестового проекта
project = Project.objects.create(
    name='Test Project',
    description='Test project for development',
    owner=client
)

print("Тестовые данные созданы!")
print(f"Client: {client.email}")
print(f"Operator: {operator.email}")
print(f"Project: {project.name}")
```

### Создание fixtures

```bash
# Создание fixtures
python manage.py dumpdata auth.User projects.Project --natural-foreign --natural-primary > fixtures/test_data.json

# Загрузка fixtures
python manage.py loaddata fixtures/test_data.json
```

### Сброс базы данных

```bash
# Удаление SQLite базы
rm backend/db.sqlite3

# Пересоздание миграций
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser
```

## 🚀 Следующие шаги

После успешной настройки:

1. **Изучите архитектуру**: `docs/ARCHITECTURE.md`
2. **Ознакомьтесь с API**: `docs/API.md`
3. **Прочитайте конфигурацию**: `CONFIGURATION.md`
4. **Изучите deployment**: `DEPLOYMENT.md`

## 💡 Советы по разработке

### Использование виртуального окружения

Всегда используйте виртуальное окружение для изоляции зависимостей:
```bash
source venv/bin/activate  # Активация
deactivate                 # Деактивация
```

### Горячие перезагрузки

Django development сервер автоматически перезагружается при изменениях кода.

### Отладка

Используйте `print()` для быстрой отладки или pdb для детальной:
```python
import pdb; pdb.set_trace()
```

### Работа с Git

Создавайте ветки для новых функций:
```bash
git checkout -b feature/new-feature
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

### Мониторинг

Следите за логами Celery worker при разработке AI pipeline:
```bash
docker compose logs -f celery-worker
```

---

Если вы столкнулись с проблемами, не описанными в этом руководстве, пожалуйста:
1. Проверьте логи: `docker compose logs -f`
2. Проверьте конфигурацию: `python backend/compliance_app/config_validator.py`
3. Создайте issue в репозитории с подробным описанием проблемы.

Удачной разработки! 🚀