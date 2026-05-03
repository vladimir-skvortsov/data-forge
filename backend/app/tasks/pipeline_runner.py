import asyncio
import logging
import time
import traceback
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from openai import APIConnectionError as OpenAIConnError
from openai import InternalServerError as OpenAIServerError
from openai import RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import metrics
from app.core.celery_app import celery_app
from app.db.enums import FileStatus, JobStatus
from app.db.models.job import Job
from app.db.models.job_result import JobResult
from app.db.session import AsyncSessionFactory
from app.services import billing_service

logger = logging.getLogger(__name__)

_RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    OpenAIConnError,
    RateLimitError,
    OpenAIServerError,
)


@celery_app.task(
    bind=True,
    name='tasks.run_pipeline',
    queue='slow_queue',
    max_retries=3,
    default_retry_delay=60,
)
def run_pipeline(self, job_id: str) -> None:
    try:
        asyncio.run(_execute(job_id))
    except _RETRYABLE_ERRORS as exc:
        logger.warning(
            'Transient error for job %s (attempt %d/%d), retrying',
            job_id,
            self.request.retries + 1,
            self.max_retries,
        )
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries)) from exc


async def _execute(job_id: str) -> None:
    start = time.monotonic()
    async with AsyncSessionFactory() as db:
        async with db.begin():
            result = await db.execute(
                select(Job)
                .options(selectinload(Job.files))
                .where(Job.id == uuid.UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job is None:
                logger.error('Job %s not found in pipeline runner', job_id)
                return

            try:
                await _process_job(job, job_id, db)
            except _RETRYABLE_ERRORS:
                raise
            except Exception:
                logger.exception('Pipeline failed for job %s', job_id)
                await _handle_failure(job, job_id, db)
            finally:
                metrics.job_processing_duration_seconds.observe(
                    time.monotonic() - start
                )


async def _process_job(job: Job, job_id: str, db: AsyncSession) -> None:
    from app.config import settings
    from app.core.result_formatter import write_results
    from app.pipeline import run_pipeline as _run_pipeline
    from app.pipeline.postprocess_blocks import deduplicate, remove_outliers

    job.status = JobStatus.PROCESSING
    for file in job.files:
        file.status = FileStatus.PROCESSING
    await db.flush()

    metrics.celery_queue_length.labels(queue='slow_queue').dec()

    pipeline_config = list(job.pipeline_config)
    schema_config = dict(job.schema_config)
    block_types = {str(b.get('type', '')) for b in pipeline_config}
    output_format = str(schema_config.get('output_format', 'json'))

    results: list[dict] = []
    for file in job.files:
        state = await _run_pipeline(file, pipeline_config, schema_config)
        results.append(
            {
                'file': file.original_name,
                'structured': state.structured_data,
                'processed_path': state.file_path,
            }
        )
        file.status = FileStatus.DONE
        metrics.files_processed_total.labels(
            file_type=file.file_type.value, status='done'
        ).inc()

    # Post-processing (operate on the aggregated result set)
    if 'deduplicate' in block_types:
        results = deduplicate(results)
    if 'remove_outliers' in block_types:
        results = remove_outliers(results)

    job_dir = Path(settings.storage_path) / job_id
    result_path = write_results(results, job_dir, output_format)

    db.add(
        JobResult(
            job_id=job.id,
            result_file_path=str(result_path),
            row_count=len(results),
        )
    )

    actual_charge = job.credits_estimate or Decimal('0')
    await billing_service.charge(
        str(job.user_id), job_id, actual_charge, actual_charge, db
    )

    job.status = JobStatus.COMPLETED
    job.credits_charged = actual_charge
    job.completed_at = datetime.now(UTC)

    metrics.jobs_total.labels(status='completed').inc()
    metrics.credits_charged_total.inc(float(actual_charge))


async def _handle_failure(job: Job, job_id: str, db: AsyncSession) -> None:
    job.status = JobStatus.FAILED
    job.error_message = traceback.format_exc()[-2000:]

    held = job.credits_estimate or Decimal('0')
    if held > 0:
        try:
            await billing_service.refund(str(job.user_id), job_id, held, db)
        except Exception:
            logger.exception('Failed to refund credits for job %s', job_id)

    for file in job.files:
        if file.status == FileStatus.PROCESSING:
            file.status = FileStatus.FAILED
            metrics.files_processed_total.labels(
                file_type=file.file_type.value, status='failed'
            ).inc()

    metrics.jobs_total.labels(status='failed').inc()
