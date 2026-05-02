FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies (cached layer — only re-runs on pyproject.toml changes)
COPY pyproject.toml ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
