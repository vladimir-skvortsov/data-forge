# DataForge

Scalable ML service for automatic structuring of unstructured data based on user-defined schemas and configurable processing pipelines.

Users upload files (text, images, audio), define a JSON schema describing the target structure, assemble a processing pipeline from ready-made blocks, and receive a structured dataset (JSON / YAML / CSV / Parquet).

## Quick start

```bash
cp .env.example .env
make dev
```

| Service     | URL                        |
|-------------|----------------------------|
| API         | http://localhost:8000      |
| API Docs    | http://localhost:8000/api/docs |
| Frontend    | http://localhost:8501      |
| Prometheus  | http://localhost:9090      |
| Grafana     | http://localhost:3000 (admin / dataforge) |
| Flower      | http://localhost:5555      |

## Local development (without Docker)

```bash
# Backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
uv sync
uv run streamlit run app.py

# Celery worker (separate terminal)
cd backend
uv run celery -A app.core.celery_app worker --loglevel=info \
  -Q fast_queue,slow_queue,postprocess_queue
```

Requires local PostgreSQL and Redis.

## Makefile targets

```
make dev        # docker compose up --build
make build      # docker compose build
make up         # docker compose up -d
make down       # docker compose down
make clean      # docker compose down -v --remove-orphans
make logs       # docker compose logs -f
make migrate    # alembic upgrade head (local)
make test       # run all tests
make lint       # ruff check
make format     # ruff format
```
