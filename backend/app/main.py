import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from decimal import Decimal

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.jobs import router as jobs_router
from app.config import settings
from app.core import metrics
from app.db.session import AsyncSessionFactory

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


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response: Response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        return response


async def _sync_metrics_loop() -> None:
    """Periodically sync business metrics from DB into Prometheus Gauges."""
    logger = logging.getLogger(__name__)
    while True:
        try:
            async with AsyncSessionFactory() as db:
                row = await db.execute(
                    text(
                        'SELECT COALESCE(SUM(credits_charged), 0) '
                        "FROM jobs WHERE status = 'completed'"
                    )
                )
                total: Decimal = row.scalar_one()
                metrics.credits_charged_total.set(float(total))
        except Exception:
            logger.exception('Failed to sync metrics from DB')
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    _instrumentator.expose(_app, endpoint='/metrics', tags=['monitoring'])
    task = asyncio.create_task(_sync_metrics_loop())
    try:
        yield
    finally:
        task.cancel()


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

    app.add_middleware(RequestIDMiddleware)
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
