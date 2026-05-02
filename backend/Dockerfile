FROM python:3.12-slim

# System dependencies: ffmpeg for pydub audio processing
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies (cached layer — only re-runs on pyproject.toml changes)
COPY pyproject.toml ./
RUN uv sync --frozen --no-dev

# Download spaCy language models (EN + RU)
RUN uv run python -m spacy download en_core_web_sm \
    && uv run python -m spacy download ru_core_news_sm

# Pre-download NLTK corpora so workers don't fetch at runtime
RUN uv run python -c "\
import nltk; \
nltk.download('stopwords', quiet=True); \
nltk.download('punkt_tab', quiet=True)"

# Copy application source
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
