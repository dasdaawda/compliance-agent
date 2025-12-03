# 🚀 AI-Комплаенс Агент - Установка и Запуск

> **Полное руководство по установке, настройке и запуску AI-Комплаенс Агента**

## 📋 Содержание

- [О системе](#о-системе)
- [Системные требования](#системные-требования)
- [Быстрая установка](#быстрая-установка)
- [Подробная настройка](#подробная-настройка)
- [Запуск системы](#запуск-системы)
- [Проверка работы](#проверка-работы)
- [Полезные команды](#полезные-команды)
- [Решение проблем](#решение-проблем)

---

## 🎯 О системе

AI-Комплаенс Агент - это система автоматического анализа видеоконтента для выявления комплаенс-рисков. Система использует AI-модели для детекции:

- 🔞 NSFW контент и эротика
- 🩸 Жесть, насилие, кровь  
- 🤬 Нецензурная лексика
- 📢 Немаркированная реклама
- 🚬 Алкоголь, табак, наркотики
- ⚠️ Запрещенная символика
- 📝 Нарушения 436-ФЗ и 20.3 КоАП

### Технологический стек

- **Backend**: Python 3.11, Django 5
- **Frontend**: Django Templates, HTMX, Bootstrap 5
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL
- **Storage**: Backblaze B2 + Cloudflare CDN
- **AI**: Replicate (Whisper, YOLO, NSFW-детекторы)

---

## 💻 Системные требования

### Обязательные компоненты

- **Python 3.11+**
- **Docker & Docker Compose** (рекомендуется)
- **Git**

### Для локальной разработки (без Docker)

- **PostgreSQL** 12+
- **Redis** 6+

### Проверка требований

```bash
# Проверка Python
python --version  # Должна быть версия 3.11+

# Проверка Docker
docker --version
docker compose --version

# Проверка Git
git --version
```

---

## ⚡ Быстрая установка (Docker)

> **Рекомендуемый способ для быстрого старта**

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd ai-compliance-agent
```

### 2. Настройка окружения

```bash
# Копируем конфигурацию для Docker
cp .env.docker .env

# Редактируем обязательные переменные
nano .env
```

**Минимально необходимые настройки в `.env`:**
```bash
# Безопасность
SECRET_KEY=your-very-secure-secret-key-here

# База данных (PostgreSQL)
POSTGRES_DB=compliance_db
POSTGRES_USER=compliance_user  
POSTGRES_PASSWORD=your-secure-password

# Redis
REDIS_URL=redis://redis:6379/0

# AI сервис (можно использовать тестовый токен)
REPLICATE_API_TOKEN=your-replicate-token

# Хранилище (можно использовать тестовые данные)
BACKBLAZE_APPLICATION_KEY_ID=your-key-id
BACKBLAZE_APPLICATION_KEY=your-secret-key
BACKBLAZE_BUCKET_NAME=your-bucket-name
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
```

### 3. Запуск системы

```bash
# Запускаем все сервисы
docker compose up -d

# Выполняем миграции базы данных
docker compose exec web python manage.py migrate

# Создаем администратора
docker compose exec web python manage.py createsuperuser

# Проверяем статус
docker compose ps
```

### 4. Доступ к системе

- **Веб-интерфейс**: http://localhost:8000
- **Админ-панель**: http://localhost:8000/admin/
- **API документация**: http://localhost:8000/api/docs/
- **Клиентский дашборд**: http://localhost:8000/client/dashboard/

---

## 🔧 Подробная настройка

### Шаг 1: Установка системных зависимостей

#### macOS с Homebrew
```bash
brew install python@3.11 postgresql redis docker-desktop
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
  postgresql postgresql-contrib redis-server docker.io docker-compose git
```

#### Fedora/CentOS
```bash
sudo dnf install -y python3.11 python3.11-devel postgresql-server redis \
  docker docker-compose git
```

### Шаг 2: Настройка базы данных PostgreSQL

```bash
# Запускаем PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создаем пользователя и базу данных
sudo -u postgres psql
```

В PostgreSQL shell:
```sql
CREATE USER compliance_user WITH PASSWORD 'your-secure-password';
CREATE DATABASE compliance_db OWNER compliance_user;
GRANT ALL PRIVILEGES ON DATABASE compliance_db TO compliance_user;
\q
```

### Шаг 3: Настройка Redis

```bash
# Запускаем Redis
sudo systemctl start redis
sudo systemctl enable redis

# Проверяем работу
redis-cli ping
# Ожидаемый ответ: PONG
```

### Шаг 4: Настройка Python окружения

```bash
# Создаем виртуальное окружение
python3.11 -m venv venv

# Активируем окружение
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements.dev.txt
```

### Шаг 5: Конфигурация проекта

```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем конфигурацию
nano .env
```

**Пример полной конфигурации `.env`:**
```bash
# Окружение
DJANGO_ENV=development
DEBUG=True
SECRET_KEY=your-very-secure-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# База данных
DATABASE_URL=postgres://compliance_user:your-secure-password@localhost:5432/compliance_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (для разработки можно использовать консоль)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# AI сервисы
REPLICATE_API_TOKEN=r8_your-replicate-token

# Хранилище B2
BACKBLAZE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
BACKBLAZE_APPLICATION_KEY_ID=your-key-id
BACKBLAZE_APPLICATION_KEY=your-secret-key
BACKBLAZE_BUCKET_NAME=your-bucket-name

# Дашборд URL
DASHBOARD_URL=http://localhost:8000/client/dashboard/
```

---

## 🚀 Запуск системы

### Вариант 1: Docker Compose (рекомендуется)

```bash
# Запуск всех сервисов
docker compose up -d

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down
```

### Вариант 2: Локальный запуск

#### Терминал 1: Django сервер

```bash
cd backend
source ../venv/bin/activate  # Активация виртуального окружения
export DJANGO_ENV=development
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
```

#### Терминал 2: Celery Worker

```bash
cd backend
source ../venv/bin/activate
export DJANGO_ENV=development
celery -A compliance_app worker --loglevel=info --concurrency=4
```

#### Терминал 3: Celery Beat (планировщик)

```bash
cd backend
source ../venv/bin/activate
export DJANGO_ENV=development
celery -A compliance_app beat --loglevel=info
```

---

## ✅ Проверка работы

### 1. Проверка конфигурации

```bash
# Docker
docker compose exec web python backend/compliance_app/config_validator.py

# Локально
python backend/compliance_app/config_validator.py
```

Ожидаемый результат:
```
✅ Configuration is valid! All variables are set correctly.
```

### 2. Проверка Django

```bash
# Docker
docker compose exec web python manage.py check --deploy

# Локально
cd backend
python manage.py check --deploy
```

### 3. Проверка API

```bash
# Проверка доступности сервера
curl http://localhost:8000/api/health/

# Проверка Swagger документации
curl http://localhost:8000/api/docs/
```

### 4. Создание тестового пользователя

```bash
# Docker
docker compose exec web python manage.py createsuperuser

# Локально
cd backend
python manage.py createsuperuser
```

### 5. Тестовый запуск

1. Откройте браузер: http://localhost:8000/admin/
2. Войдите с созданными учетными данными
3. Создайте тестовый проект
4. Загрузите тестовое видео
5. Проверьте запуск AI-анализа

---

## 🛠️ Полезные команды

### Docker Compose команды

```bash
# Запуск всех сервисов
docker compose up -d

# Пересборка с кэшем
docker compose up -d --build

# Полная пересборка без кэша
docker compose up -d --build --no-cache

# Просмотр логов
docker compose logs -f web
docker compose logs -f celery-worker
docker compose logs -f celery-beat

# Выполнение команд в контейнере
docker compose exec web python manage.py shell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Очистка
docker compose down -v  # С удалением томов
docker system prune -f  # Очистка неиспользуемых образов
```

### Команды разработки

```bash
# Создание миграций
cd backend
python manage.py makemigrations
python manage.py migrate

# Запуск тестов
python manage.py test

# Линтинг кода
flake8 backend/
black backend/
isort backend/

# Django shell
python manage.py shell

# Проверка зависимостей
pip-audit  # Проверка уязвимостей
pip list   # Список установленных пакетов
```

### Мониторинг

```bash
# Проверка статуса сервисов
docker compose ps

# Мониторинг ресурсов
docker stats

# Проверка Redis
redis-cli info memory

# Проверка PostgreSQL
docker compose exec postgres psql -U compliance_user -d compliance_db -c "\dt"
```

---

## 🐛 Решение проблем

### Частые проблемы

#### 1. Ошибка: `python: command not found`

**Решение:**
```bash
# Убедитесь что Python 3.11 установлен
python3.11 --version

# Используйте python3.11 вместо python
python3.11 -m venv venv
```

#### 2. Ошибка: `redis: connection refused`

**Решение:**
```bash
# Проверьте статус Redis
sudo systemctl status redis

# Запустите Redis
sudo systemctl start redis

# Для Docker проверьте контейнер
docker compose ps redis
docker compose logs redis
```

#### 3. Ошибка: `FATAL: database "compliance_db" does not exist`

**Решение:**
```bash
# Создайте базу данных
sudo -u postgres createdb compliance_db

# Или используйте миграции
docker compose exec web python manage.py migrate
```

#### 4. Ошибка: `ModuleNotFoundError: No module named 'django'`

**Решение:**
```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

#### 5. Ошибка: `Permission denied` при запуске Docker

**Решение:**
```bash
# Добавьте пользователя в группу docker
sudo usermod -aG docker $USER

# Перезайдите в систему или используйте:
newgrp docker
```

### Очистка и переустановка

```bash
# Полная очистка Docker
docker compose down -v
docker system prune -af
docker volume prune -f

# Переустановка зависимостей
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements.dev.txt

# Пересоздание базы данных
docker compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS compliance_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE compliance_db OWNER compliance_user;"
docker compose exec web python manage.py migrate
```

### Получение помощи

1. **Проверьте логи**: `docker compose logs -f`
2. **Проверьте конфигурацию**: `python backend/compliance_app/config_validator.py`
3. **Проверьте системные требования**: версии Python, Docker, PostgreSQL, Redis
4. **Изучите документацию**: `docs/` директория содержит подробные руководства

---

## 📚 Дополнительная документация

- **[📖 Полная документация](docs/README.md)** - исчерпывающая документация
- **[🏗️ Архитектура системы](docs/ARCHITECTURE.md)** - подробное описание архитектуры
- **[🔌 API документация](docs/API.md)** - полное описание REST API
- **[⚙️ Конфигурация](docs/CONFIGURATION.md)** - все настройки и переменные
- **[🚀 Production развертывание](docs/DEPLOYMENT.md)** - руководство по продакшн развертыванию
- **[🔧 Разработка](docs/DEVELOPMENT.md)** - руководство для разработчиков

---

## 🎉 Готово!

После выполнения этих шагов у вас будет полностью работающая система AI-Комплаенс Агент. Вы можете:

1. Загружать видео через веб-интерфейс
2. Отслеживать процесс AI-анализа
3. Просматривать отчеты о рисках
4. Использовать REST API для интеграций
5. Настраивать верификацию операторами

**Начните с:** http://localhost:8000/client/dashboard/

---

*Если у вас возникли вопросы или проблемы, обратитесь к разделу [Решение проблем](#решение-проблем) или изучите подробную документацию в директории `docs/`.*
