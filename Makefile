.PHONY: help install run migrate makemigrations shell celery-worker celery-beat up down test

PYTHON = .venv/bin/python
PIP    = .venv/bin/pip
MANAGE = $(PYTHON) manage.py

help:
	@echo "Available commands:"
	@echo "  make install         Install Python dependencies"
	@echo "  make up              Start PostgreSQL + Redis via Docker"
	@echo "  make down            Stop Docker services"
	@echo "  make migrate         Apply database migrations"
	@echo "  make makemigrations  Create new migrations"
	@echo "  make run             Start the Django development server"
	@echo "  make celery-worker   Start Celery worker"
	@echo "  make celery-beat     Start Celery beat scheduler"
	@echo "  make shell           Open Django shell"
	@echo "  make superuser       Create a Django superuser"

install:
	$(PIP) install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

run:
	$(MANAGE) runserver

celery-worker:
	.venv/bin/celery -A config.celery worker --loglevel=info

celery-beat:
	.venv/bin/celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

shell:
	$(MANAGE) shell

superuser:
	$(MANAGE) createsuperuser

check:
	$(MANAGE) check
