.PHONY: up down build logs test lint fmt install install-playwright

up:
	docker compose up --build -d

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

test:
	pytest tests/ -v --tb=short

lint:
	ruff check app tests

fmt:
	ruff format app tests

install:
	pip install -e ".[dev]"

install-playwright:
	python -m playwright install chromium
