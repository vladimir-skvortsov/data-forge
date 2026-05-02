.PHONY: dev build up down clean logs \
        migrate test test-backend test-frontend lint format

dev:
	docker compose up --build

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

clean:
	docker compose down -v --remove-orphans

logs:
	docker compose logs -f

migrate:
	cd backend && uv run alembic upgrade head

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && uv run pytest

test: test-backend test-frontend

lint:
	uv run ruff check backend frontend

format:
	uv run ruff format backend frontend
