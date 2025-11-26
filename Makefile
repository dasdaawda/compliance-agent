# AI-Compliance Agent - Development Makefile
# Common commands for development and deployment

.PHONY: help install dev-install test lint format docker-up docker-down migrate shell clean

# Default target
help:
	@echo "AI-Compliance Agent - Available Commands:"
	@echo ""
	@echo "  Development:"
	@echo "    make install       - Install production dependencies"
	@echo "    make dev-install   - Install dev dependencies"
	@echo "    make migrate       - Run database migrations"
	@echo "    make shell         - Open Django shell"
	@echo "    make superuser     - Create superuser"
	@echo "    make collectstatic - Collect static files"
	@echo ""
	@echo "  Testing & Quality:"
	@echo "    make test          - Run tests"
	@echo "    make test-coverage - Run tests with coverage"
	@echo "    make lint          - Run linting (flake8)"
	@echo "    make format        - Format code (black, isort)"
	@echo "    make check         - Run Django system checks"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-build  - Build Docker images"
	@echo "    make docker-up     - Start all services"
	@echo "    make docker-down   - Stop all services"
	@echo "    make docker-logs   - View logs"
	@echo "    make docker-shell  - Open shell in web container"
	@echo "    make docker-migrate - Run migrations in Docker"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean         - Remove Python cache files"
	@echo "    make clean-docker  - Remove Docker volumes"
	@echo ""

# Installation
install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt -r requirements.dev.txt

# Django commands
migrate:
	cd backend && python manage.py migrate

makemigrations:
	cd backend && python manage.py makemigrations

shell:
	cd backend && python manage.py shell

superuser:
	cd backend && python manage.py createsuperuser

collectstatic:
	cd backend && python manage.py collectstatic --noinput

runserver:
	cd backend && python manage.py runserver

# Testing & Quality
test:
	cd backend && python manage.py test

test-coverage:
	cd backend && pytest --cov=. --cov-report=html --cov-report=term

lint:
	flake8 backend/

format:
	black backend/
	isort backend/

check:
	cd backend && python manage.py check --deploy

validate-config:
	python backend/compliance_app/config_validator.py

# Docker commands
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-shell:
	docker compose exec web bash

docker-migrate:
	docker compose exec web python manage.py migrate

docker-superuser:
	docker compose exec web python manage.py createsuperuser

docker-test:
	docker compose exec web python manage.py test

docker-restart-web:
	docker compose restart web

docker-restart-celery:
	docker compose restart celery-worker

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .pytest_cache htmlcov .coverage

clean-docker:
	docker compose down -v

# Database
db-backup:
	docker compose exec postgres pg_dump -U postgres ai_compliance_db > backup_$$(date +%Y%m%d_%H%M%S).sql

db-restore:
	@echo "Usage: cat backup_YYYYMMDD_HHMMSS.sql | docker compose exec -T postgres psql -U postgres ai_compliance_db"

# Celery
celery-worker:
	cd backend && celery -A compliance_app worker --loglevel=info

celery-beat:
	cd backend && celery -A compliance_app beat --loglevel=info

celery-status:
	cd backend && celery -A compliance_app inspect active

# Production deployment
deploy-check: validate-config check test
	@echo "✅ All pre-deployment checks passed!"
