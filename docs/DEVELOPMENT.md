# 🛠️ Руководство по разработке

## Содержание
1. [Быстрый старт](#быстрый-старт)
2. [Локальная разработка](#локальная-разработка)
3. [Работа с базой данных](#работа-с-базой-данных)
4. [Тестирование](#тестирование)
5. [Линтинг и форматирование](#линтинг-и-форматирование)
6. [Полезные команды](#полезные-команды)

---

## Быстрый старт

### Вариант A: Docker Compose (рекомендуется)

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

### Вариант B: Локальная разработка без Docker

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

# В третьем терминале запустите Celery Beat (для периодических задач)
celery -A compliance_app beat --loglevel=info
```

---

## Локальная разработка

### Настройка переменных окружения

Для локальной разработки создайте `.env` файл:

```bash
# Скопируйте пример
cp .env.example .env

# Или используйте скрипт
./setup_env.sh

# Откройте и отредактируйте
nano .env
```

**Минимальные настройки для разработки:**

```env
DJANGO_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0

# Опционально для тестирования AI pipeline
REPLICATE_API_TOKEN=r8_your_token_here
BACKBLAZE_APPLICATION_KEY_ID=your_key_id
BACKBLAZE_APPLICATION_KEY=your_key
BACKBLAZE_BUCKET_NAME=your-bucket
```

Подробнее о переменных окружения см. [CONFIGURATION.md](CONFIGURATION.md)

### Структура проекта

```
ai-compliance-agent/
├── backend/                    # Django приложение
│   ├── compliance_app/         # Основные настройки
│   │   ├── settings/           # Модульные настройки Django
│   │   │   ├── __init__.py     # Автоматический выбор окружения
│   │   │   ├── base.py         # Общие настройки
│   │   │   ├── dev.py          # Настройки разработки
│   │   │   └── prod.py         # Настройки production
│   │   ├── celery.py           # Настройки Celery
│   │   └── config_validator.py # Валидатор конфигурации
│   ├── users/                  # Управление пользователями
│   ├── projects/               # Проекты и видео
│   ├── ai_pipeline/            # AI обработка
│   │   ├── celery_tasks.py     # Celery задачи
│   │   └── services/           # AI сервисы (Whisper, YOLO, etc)
│   ├── operators/              # Рабочий стол оператора
│   ├── admins/                 # Админ-панель
│   ├── storage/                # Интеграция с B2/Cloudflare
│   └── templates/              # Django Templates + HTMX
├── scripts/                    # Вспомогательные скрипты
│   └── entrypoint.sh           # Docker entrypoint
├── celery-worker/              # Скрипты Celery worker
├── docs/                       # Документация
├── requirements.txt            # Python зависимости (pinned)
├── requirements.dev.txt        # Зависимости для разработки
└── docker-compose.yml          # Docker Compose для разработки
```

---

## Работа с базой данных

### Создание миграций

```bash
cd backend

# Создать миграции для всех приложений
python manage.py makemigrations

# Создать миграции для конкретного приложения
python manage.py makemigrations projects

# Просмотреть SQL миграции
python manage.py sqlmigrate projects 0001

# Применить миграции
python manage.py migrate

# Откатить миграции
python manage.py migrate projects 0001
```

### Работа с данными

```bash
# Открыть Django shell
python manage.py shell

# Открыть database shell
python manage.py dbshell

# Создать суперпользователя
python manage.py createsuperuser

# Загрузить фикстуры
python manage.py loaddata fixtures/initial_data.json

# Выгрузить данные
python manage.py dumpdata projects --indent 2 > fixtures/projects.json
```

### Сброс базы данных (локально)

```bash
# SQLite
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser

# PostgreSQL (Docker)
docker compose down -v
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

---

## Тестирование

### Запуск тестов

```bash
cd backend

# Запустить все тесты
python manage.py test

# Запустить тесты конкретного приложения
python manage.py test projects

# Запустить конкретный тест
python manage.py test projects.tests.test_api.ProjectAPITestCase

# Запустить с coverage
coverage run --source='.' manage.py test
coverage report
coverage html

# Запустить через pytest (если установлен)
pytest
pytest -v -s  # verbose с выводом print
pytest --cov=backend --cov-report=html
```

### Запуск тестов в Docker

```bash
# Запустить все тесты
docker compose exec web python manage.py test

# С coverage
docker compose exec web coverage run --source='.' manage.py test
docker compose exec web coverage report
```

---

## Линтинг и форматирование

### Flake8 (линтинг)

```bash
# Проверить весь проект
flake8 backend/

# Проверить конкретное приложение
flake8 backend/projects/

# Игнорировать определенные ошибки
flake8 backend/ --ignore=E501,W503
```

### Black (форматирование)

```bash
# Проверить без изменений
black --check backend/

# Применить форматирование
black backend/

# Проверить конкретный файл
black backend/projects/views.py
```

### isort (сортировка импортов)

```bash
# Проверить без изменений
isort --check-only backend/

# Применить сортировку
isort backend/
```

---

## Полезные команды

### Makefile

Проект включает Makefile с полезными командами:

```bash
# Просмотр всех доступных команд
make help

# Docker разработка
make docker-up           # Запустить все сервисы
make docker-migrate      # Выполнить миграции
make docker-logs         # Просмотр логов
make docker-shell        # Открыть shell в контейнере
make docker-down         # Остановить сервисы

# Локальная разработка
make install            # Установить зависимости
make migrate            # Выполнить миграции
make test               # Запустить тесты
make lint               # Проверить код
make format             # Форматировать код
make run                # Запустить сервер разработки
```

### Django management команды

```bash
# Создать приложение
python manage.py startapp myapp

# Собрать статику
python manage.py collectstatic --noinput

# Очистить сессии
python manage.py clearsessions

# Проверить настройки для production
python manage.py check --deploy

# Создать кастомную команду
python manage.py my_custom_command
```

### Celery команды

```bash
# Запустить worker
celery -A compliance_app worker --loglevel=info

# Запустить worker с автоперезагрузкой
watchmedo auto-restart --directory=./backend/ --pattern=*.py --recursive -- celery -A compliance_app worker --loglevel=info

# Запустить beat (периодические задачи)
celery -A compliance_app beat --loglevel=info

# Просмотр активных задач
celery -A compliance_app inspect active

# Просмотр зарегистрированных задач
celery -A compliance_app inspect registered

# Отменить задачу
celery -A compliance_app control revoke <task_id>

# Очистить все задачи
celery -A compliance_app purge
```

### Docker команды

```bash
# Пересобрать контейнеры
docker compose build

# Запустить в фоне
docker compose up -d

# Остановить и удалить volumes
docker compose down -v

# Просмотр логов конкретного сервиса
docker compose logs -f web
docker compose logs -f celery-worker

# Выполнить команду в контейнере
docker compose exec web python manage.py shell
docker compose exec web bash

# Просмотр запущенных контейнеров
docker compose ps

# Перезапустить сервис
docker compose restart web
```

---

## Отладка

### Django Debug Toolbar

В режиме разработки (`DJANGO_ENV=development`) доступен Django Debug Toolbar:

```python
# Добавлен в settings/dev.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

Откройте `http://localhost:8000/__debug__/` для просмотра панели.

### Логирование

Настройки логирования в `settings/base.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'ai_pipeline': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Celery Flower (мониторинг задач)

```bash
# Установить
pip install flower

# Запустить
celery -A compliance_app flower

# Открыть в браузере
open http://localhost:5555
```

---

## Troubleshooting

### Проблема: ModuleNotFoundError

```bash
# Убедитесь, что находитесь в правильной директории
cd backend

# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Переустановите зависимости
pip install -r requirements.txt
```

### Проблема: OperationalError (database locked)

SQLite не поддерживает конкурентную запись. Используйте PostgreSQL:

```bash
# С Docker Compose
docker compose up -d

# Или установите PostgreSQL локально
export DATABASE_URL=postgresql://user:password@localhost/dbname
```

### Проблема: Connection refused (Redis/Celery)

```bash
# Проверьте, что Redis запущен
redis-cli ping

# Запустите Redis
redis-server

# Или используйте Docker
docker run -d -p 6379:6379 redis:alpine
```

### Проблема: Static files не загружаются

```bash
# Соберите статику
python manage.py collectstatic --noinput

# В development режиме Django сам обслуживает статику
# В production используйте WhiteNoise или nginx
```

---

## Полезные ресурсы

- [Django Documentation](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [HTMX Documentation](https://htmx.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

## Следующие шаги

После настройки локальной разработки:

1. Изучите [API.md](API.md) для работы с REST API
2. Изучите [ARCHITECTURE.md](ARCHITECTURE.md) для понимания архитектуры
3. Изучите [CONFIGURATION.md](CONFIGURATION.md) для настройки переменных окружения
4. Изучите [DEPLOYMENT.md](DEPLOYMENT.md) для деплоя на production

---

**Удачной разработки! 🚀**
