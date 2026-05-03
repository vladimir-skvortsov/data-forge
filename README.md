# DataForge

Scalable ML service for automatic structuring of unstructured data based on user-defined schemas and configurable processing pipelines.

Users upload files (text, images, audio), define a JSON schema describing the target structure, assemble a processing pipeline from ready-made blocks, and receive a structured dataset (JSON / YAML / CSV / Parquet).

## Quick start

```bash
cp .env.example .env
make dev
```

| Service    | URL                                           |
|------------|-----------------------------------------------|
| API        | http://localhost:8000                         |
| API Docs   | http://localhost:8000/api/docs (Swagger)      |
| Frontend   | http://localhost:8501                         |
| Prometheus | http://localhost:9090                         |
| Grafana    | http://localhost:3000 (`admin` / `dataforge`) |
| Flower     | http://localhost:5555                         |

## Business model

**UTP:** DataForge replaces manual ETL scripting — assemble a pipeline in the UI, define the output schema, get a structured dataset in minutes. No code required.

**Pricing rationale (pay-as-you-go):**

| Resource           | Cost driver                              | Price              |
|--------------------|------------------------------------------|--------------------|
| Text file          | CPU parse time + LLM tokens              | 1 cr / 2 000 chars |
| Image              | Vision LLM call (fixed cost per image)   | 3 cr / image       |
| Audio              | Whisper STT (proportional to duration)   | 2 cr / minute      |
| LLM pipeline block | Extra OpenRouter call                    | 0.5–1 cr / file    |
| Post-processing    | CPU (scikit-learn IsolationForest)       | 2 cr / job         |

1 credit ≈ 1 RUB in a real deployment. Prices are calibrated so that OpenRouter API costs
(≈$0.001–0.01 per LLM call) are covered with a ~3x margin.

A job is considered successful when the pipeline completes without an unhandled exception on the server side — regardless of the semantic quality of the LLM output. Credits are charged only on success; returned in full on any server-side failure.

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
