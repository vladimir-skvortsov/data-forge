from openai import APIError, AsyncOpenAI

from app.config import settings

openrouter: AsyncOpenAI = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
)


def get_client() -> AsyncOpenAI:
    return openrouter


async def safe_chat_completion(**kwargs: object) -> object:
    from app.core.metrics import openrouter_api_errors_total

    try:
        return await openrouter.chat.completions.create(**kwargs)  # type: ignore[arg-type]
    except APIError:
        openrouter_api_errors_total.inc()
        raise


async def safe_audio_transcription(**kwargs: object) -> object:
    from app.core.metrics import openrouter_api_errors_total

    try:
        return await openrouter.audio.transcriptions.create(**kwargs)  # type: ignore[arg-type]
    except APIError:
        openrouter_api_errors_total.inc()
        raise
