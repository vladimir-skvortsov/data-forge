from openai import AsyncOpenAI

from app.config import settings

openrouter: AsyncOpenAI = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
)


def get_client() -> AsyncOpenAI:
    return openrouter
