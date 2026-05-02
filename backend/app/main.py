import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.jobs import router as jobs_router
from app.config import settings

_API_V1_PREFIX = '/api/v1'
_instrumentator = Instrumentator(should_group_status_codes=True)


def _configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer()
            if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format='%(message)s',
        level=logging.DEBUG if settings.debug else logging.INFO,
    )


_configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    _instrumentator.expose(_app, endpoint='/metrics', tags=['monitoring'])
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

    _instrumentator.instrument(app)

    app.include_router(auth_router, prefix=_API_V1_PREFIX)
    app.include_router(billing_router, prefix=_API_V1_PREFIX)
    app.include_router(jobs_router, prefix=_API_V1_PREFIX)
    app.include_router(dashboard_router, prefix=_API_V1_PREFIX)

    return app


app = create_app()


@app.get('/health', tags=['system'])
async def health() -> dict[str, str]:
    return {'status': 'ok'}
