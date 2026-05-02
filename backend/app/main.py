from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title='DataForge API',
        version='0.1.0',
        description='Automatic document structuring service',
        docs_url='/api/docs',
        redoc_url='/api/redoc',
        openapi_url='/api/openapi.json',
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.include_router(auth_router, prefix='/api/v1')

    return app


app = create_app()


@app.get('/health', tags=['system'])
async def health() -> dict[str, str]:
    return {'status': 'ok'}
