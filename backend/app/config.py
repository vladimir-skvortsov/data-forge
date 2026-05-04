"""Application configuration via Pydantic Settings."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / '.env'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ENV_FILE), '.env'),
        env_file_encoding='utf-8',
        case_sensitive=False,
    )

    # Application
    app_env: str = 'development'
    debug: bool = False

    # Database
    postgres_url: str = (
        'postgresql+asyncpg://postgres:postgres@localhost:5432/dataforge'
    )

    # Redis / Celery
    redis_url: str = 'redis://localhost:6379/0'
    celery_broker_url: str = 'redis://localhost:6379/0'
    celery_result_backend: str = 'redis://localhost:6379/1'

    # JWT — must be set via env in any real deployment
    jwt_secret_key: str = ''
    jwt_algorithm: str = 'HS256'
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # OpenRouter
    openrouter_api_key: str = ''
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openrouter_llm_model: str = 'moonshotai/kimi-k2.5:nitro'
    openrouter_vision_model: str = 'moonshotai/kimi-k2.5:nitro'
    openrouter_stt_model: str = 'openai/whisper-1'

    # File storage
    storage_path: str = '/app/storage'
    max_file_size_mb: int = 400
    max_files_per_job: int = 100

    # CORS
    cors_origins: str | list[str] = ['http://localhost:8501']

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return list(v)


settings = Settings()
