import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core import metrics
from app.core.cost_estimator import estimate_breakdown, estimate_cost
from app.core.result_formatter import read_results
from app.db.enums import FileStatus, FileType, JobStatus
from app.db.models.job import Job
from app.db.models.job_file import JobFile
from app.db.models.job_result import JobResult
from app.services import billing_service
from app.services.billing_service import InsufficientBalanceError
from app.tasks.pipeline_runner import run_pipeline

_EXTENSION_TO_FILE_TYPE: dict[str, FileType] = {
    '.txt': FileType.TEXT,
    '.pdf': FileType.TEXT,
    '.docx': FileType.TEXT,
    '.md': FileType.TEXT,
    '.csv': FileType.TEXT,
    '.png': FileType.IMAGE,
    '.jpg': FileType.IMAGE,
    '.jpeg': FileType.IMAGE,
    '.webp': FileType.IMAGE,
    '.gif': FileType.IMAGE,
    '.mp3': FileType.AUDIO,
    '.wav': FileType.AUDIO,
    '.m4a': FileType.AUDIO,
    '.ogg': FileType.AUDIO,
    '.flac': FileType.AUDIO,
}


class JobNotFoundError(Exception):
    pass


class JobAccessDeniedError(Exception):
    pass


class JobStateError(Exception):
    pass


class FileLimitExceededError(Exception):
    pass


class FileSizeLimitError(Exception):
    pass


def _detect_file_type(filename: str) -> FileType:
    ext = Path(filename).suffix.lower()
    return _EXTENSION_TO_FILE_TYPE.get(ext, FileType.TEXT)


async def _load_job(job_id: str, db: AsyncSession) -> Job:
    result = await db.execute(
        select(Job).options(selectinload(Job.files)).where(Job.id == uuid.UUID(job_id))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise JobNotFoundError(job_id)
    return job


async def _load_job_with_result(job_id: str, db: AsyncSession) -> Job:
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.files), selectinload(Job.result))
        .where(Job.id == uuid.UUID(job_id))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise JobNotFoundError(job_id)
    return job


async def create_job(
    user_id: str,
    title: str,
    pipeline_config: list[dict[str, Any]],
    db: AsyncSession,
) -> Job:
    job = Job(
        user_id=uuid.UUID(user_id),
        title=title,
        status=JobStatus.DRAFT,
        pipeline_config=pipeline_config,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job, attribute_names=['files'])
    return job


async def get_job(job_id: str, user_id: str, db: AsyncSession) -> Job:
    job = await _load_job(job_id, db)
    if str(job.user_id) != user_id:
        raise JobAccessDeniedError(job_id)
    return job


async def list_jobs(user_id: str, db: AsyncSession) -> list[Job]:
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.files))
        .where(Job.user_id == uuid.UUID(user_id))
        .order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_job(job_id: str, user_id: str, db: AsyncSession) -> None:
    job = await get_job(job_id, user_id, db)
    if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
        raise JobStateError(f'Cannot delete a job while it is {job.status}')
    await db.delete(job)


async def add_file(
    job_id: str,
    user_id: str,
    upload: UploadFile,
    db: AsyncSession,
) -> JobFile:
    job = await get_job(job_id, user_id, db)
    if job.status != JobStatus.DRAFT:
        raise JobStateError('Files can only be added to draft jobs')
    if len(job.files) >= settings.max_files_per_job:
        raise FileLimitExceededError(f'Max {settings.max_files_per_job} files per job')

    content = await upload.read()
    file_size = len(content)

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise FileSizeLimitError(f'File exceeds {settings.max_file_size_mb} MB limit')

    filename = upload.filename or 'file'
    file_type = _detect_file_type(filename)

    storage_dir = Path(settings.storage_path) / str(job.id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    file_path = storage_dir / safe_name
    counter = 1
    while file_path.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        file_path = storage_dir / f'{stem}_{counter}{suffix}'
        counter += 1

    file_path.write_bytes(content)

    job_file = JobFile(
        job_id=job.id,
        original_name=filename,
        file_type=file_type,
        file_path=str(file_path),
        file_size_bytes=file_size,
        status=FileStatus.QUEUED,
    )
    db.add(job_file)
    await db.flush()
    return job_file


async def run_job(job_id: str, user_id: str, db: AsyncSession) -> tuple[Job, Decimal]:
    job = await get_job(job_id, user_id, db)
    if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
        raise JobStateError(f'Job is already running (status: {job.status})')
    if not job.files:
        raise JobStateError('Cannot run a job with no files')

    # Re-run: purge previous result and reset per-file state
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        await db.execute(delete(JobResult).where(JobResult.job_id == uuid.UUID(job_id)))
        for f in job.files:
            f.status = FileStatus.QUEUED
        job.error_message = None
        job.completed_at = None

    estimate = estimate_cost(list(job.files), list(job.pipeline_config))

    try:
        await billing_service.hold(user_id, job_id, estimate, db)
    except InsufficientBalanceError:
        raise

    job.status = JobStatus.PENDING
    job.credits_estimate = estimate
    await db.flush()

    run_pipeline.apply_async(args=[job_id], queue='slow_queue')
    metrics.celery_queue_length.labels(queue='slow_queue').inc()

    return job, estimate


async def get_job_result(
    job_id: str,
    user_id: str,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    job = await _load_job_with_result(job_id, db)
    if str(job.user_id) != user_id:
        raise JobAccessDeniedError(job_id)
    if job.status != JobStatus.COMPLETED:
        raise JobStateError(f'Job is not completed (status: {job.status})')
    if not job.result:
        raise JobStateError('No result available')
    result_path = Path(job.result.result_file_path)
    if not result_path.exists():
        raise JobStateError('Result file not found on disk')

    return read_results(result_path)


async def get_result_file_path(
    job_id: str,
    user_id: str,
    db: AsyncSession,
) -> tuple[Path, str]:
    job = await _load_job_with_result(job_id, db)
    if str(job.user_id) != user_id:
        raise JobAccessDeniedError(job_id)
    if job.status != JobStatus.COMPLETED:
        raise JobStateError(f'Job is not completed (status: {job.status})')
    if not job.result:
        raise JobStateError('No result available')
    result_path = Path(job.result.result_file_path)
    if not result_path.exists():
        raise JobStateError('Result file not found on disk')
    return result_path, result_path.name


async def get_estimate(
    job_id: str,
    user_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    job = await get_job(job_id, user_id, db)
    breakdown = estimate_breakdown(list(job.files), list(job.pipeline_config))
    total = estimate_cost(list(job.files), list(job.pipeline_config))
    balance = await billing_service.get_balance(user_id, db)
    return {
        'breakdown': breakdown,
        'total_credits': total,
        'current_balance': balance,
        'can_proceed': balance >= total,
    }


async def retry_job(job_id: str, user_id: str, db: AsyncSession) -> Job:
    job = await get_job(job_id, user_id, db)
    if job.status != JobStatus.FAILED:
        raise JobStateError(f'Cannot retry a job with status {job.status}')
    # Remove stale result row so the runner can INSERT fresh on next run
    await db.execute(delete(JobResult).where(JobResult.job_id == uuid.UUID(job_id)))
    job.status = JobStatus.DRAFT
    job.error_message = None
    for f in job.files:
        f.status = FileStatus.QUEUED
    await db.flush()
    await db.refresh(job)
    return job
