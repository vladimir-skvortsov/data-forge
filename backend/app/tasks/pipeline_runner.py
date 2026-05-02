import asyncio
import logging
import traceback
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.db.enums import FileStatus, JobStatus
from app.db.models.job import Job
from app.db.models.job_result import JobResult
from app.db.session import AsyncSessionFactory
from app.services import billing_service

if TYPE_CHECKING:
    from app.db.models.job_file import JobFile

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True, name='tasks.run_pipeline', queue='slow_queue', max_retries=0
)
def run_pipeline(self, job_id: str) -> None:  # noqa: ARG002
    asyncio.run(_execute(job_id))


async def _execute(job_id: str) -> None:
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
            except Exception:
                logger.exception('Pipeline failed for job %s', job_id)
                await _handle_failure(job, job_id, db)


async def _process_job(job: Job, job_id: str, db: object) -> None:
    job.status = JobStatus.PROCESSING

    for file in job.files:
        file.status = FileStatus.PROCESSING
    await db.flush()  # type: ignore[union-attr]

    for file in job.files:
        _apply_pipeline(file, list(job.pipeline_config))
        file.status = FileStatus.DONE

    db.add(  # type: ignore[union-attr]
        JobResult(
            job_id=job.id,
            result_file_path=f'{job_id}/result.json',
            row_count=len(job.files),
        )
    )

    actual_charge = job.credits_estimate or Decimal('0')
    await billing_service.charge(
        str(job.user_id), job_id, actual_charge, actual_charge, db
    )  # type: ignore[arg-type]

    job.status = JobStatus.COMPLETED
    job.credits_charged = actual_charge
    job.completed_at = datetime.now(UTC)


async def _handle_failure(job: Job, job_id: str, db: object) -> None:
    job.status = JobStatus.FAILED
    job.error_message = traceback.format_exc()[-2000:]

    held = job.credits_estimate or Decimal('0')
    if held > 0:
        try:
            await billing_service.refund(str(job.user_id), job_id, held, db)  # type: ignore[arg-type]
        except Exception:
            logger.exception('Failed to refund credits for job %s', job_id)

    for file in job.files:
        if file.status == FileStatus.PROCESSING:
            file.status = FileStatus.FAILED


def _apply_pipeline(file: 'JobFile', pipeline_config: list[dict]) -> None:
    for block in pipeline_config:
        block_type = block.get('type', '')
        _dispatch_block(file, block_type, block.get('params', {}))


def _dispatch_block(file: 'JobFile', block_type: str, params: dict) -> None:  # noqa: ARG001
    from app.db.enums import FileType

    _IMAGE_BLOCKS = {
        'image_resize',
        'image_upscale',
        'image_enhance',
        'image_grayscale',
    }
    _AUDIO_BLOCKS = {
        'audio_remove_silence',
        'audio_normalize',
        'audio_boost_volume',
        'audio_denoise',
    }
    _TEXT_BLOCKS = {
        'extract_text',
        'translate',
        'lemmatize',
        'remove_stopwords',
        'structure',
    }

    if block_type in _IMAGE_BLOCKS and file.file_type != FileType.IMAGE:
        return
    if block_type in _AUDIO_BLOCKS and file.file_type != FileType.AUDIO:
        return
    if block_type in _TEXT_BLOCKS and file.file_type not in (
        FileType.TEXT,
        FileType.IMAGE,
        FileType.AUDIO,
    ):
        return

    logger.debug('Applying block %s to file %s (stub)', block_type, file.id)
