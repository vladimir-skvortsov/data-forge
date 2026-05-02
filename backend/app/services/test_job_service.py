import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.enums import FileType, JobStatus
from app.db.models.job import Job
from app.db.models.job_file import JobFile
from app.services.job_service import (
    FileLimitExceededError,
    FileSizeLimitError,
    JobAccessDeniedError,
    JobNotFoundError,
    JobStateError,
    add_file,
    create_job,
    delete_job,
    get_job,
    list_jobs,
    run_job,
)


def _job(
    status: JobStatus = JobStatus.DRAFT,
    user_id: str | None = None,
    files: list | None = None,
) -> Job:
    j = MagicMock(spec=Job)
    j.id = uuid.uuid4()
    j.user_id = uuid.UUID(user_id) if user_id else uuid.uuid4()
    j.status = status
    j.files = files or []
    j.pipeline_config = []
    j.credits_estimate = None
    return j


def _db_returning(obj: object | None) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    db.execute.return_value = result
    return db


def _db_returning_all(objs: list) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = objs
    db.execute.return_value = result
    return db


@pytest.mark.anyio
async def test_create_job_creates_draft() -> None:
    db = AsyncMock()
    db.add = MagicMock()

    uid = str(uuid.uuid4())
    await create_job(uid, 'My Job', {}, [], db)

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.status == JobStatus.DRAFT
    assert added.title == 'My Job'


@pytest.mark.anyio
async def test_get_job_not_found_raises() -> None:
    db = _db_returning(None)
    with pytest.raises(JobNotFoundError):
        await get_job(str(uuid.uuid4()), 'user-1', db)


@pytest.mark.anyio
async def test_get_job_wrong_user_raises() -> None:
    job = _job(user_id=str(uuid.uuid4()))
    db = _db_returning(job)
    with pytest.raises(JobAccessDeniedError):
        await get_job(str(job.id), str(uuid.uuid4()), db)  # different user


@pytest.mark.anyio
async def test_get_job_owner_ok() -> None:
    uid = str(uuid.uuid4())
    job = _job(user_id=uid)
    db = _db_returning(job)
    result = await get_job(str(job.id), uid, db)
    assert result is job


@pytest.mark.anyio
async def test_list_jobs_returns_all() -> None:
    uid = str(uuid.uuid4())
    jobs = [_job(user_id=uid), _job(user_id=uid)]
    db = _db_returning_all(jobs)
    result = await list_jobs(uid, db)
    assert len(result) == 2


@pytest.mark.anyio
async def test_delete_draft_job_ok() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.DRAFT, user_id=uid)
    db = _db_returning(job)
    await delete_job(str(job.id), uid, db)
    db.delete.assert_called_once_with(job)


@pytest.mark.anyio
async def test_delete_failed_job_ok() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.FAILED, user_id=uid)
    db = _db_returning(job)
    await delete_job(str(job.id), uid, db)
    db.delete.assert_called_once_with(job)


@pytest.mark.anyio
async def test_delete_running_job_raises() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.PROCESSING, user_id=uid)
    db = _db_returning(job)
    with pytest.raises(JobStateError):
        await delete_job(str(job.id), uid, db)


@pytest.mark.anyio
async def test_add_file_to_non_draft_raises() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.PENDING, user_id=uid)
    db = _db_returning(job)
    upload = MagicMock()
    with pytest.raises(JobStateError):
        await add_file(str(job.id), uid, upload, db)


@pytest.mark.anyio
async def test_add_file_exceeds_limit_raises() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.DRAFT, user_id=uid, files=[MagicMock()] * 100)
    db = _db_returning(job)
    upload = MagicMock()
    with pytest.raises(FileLimitExceededError):
        await add_file(str(job.id), uid, upload, db)


@pytest.mark.anyio
async def test_add_file_size_too_large_raises() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.DRAFT, user_id=uid)
    db = _db_returning(job)
    upload = AsyncMock()
    upload.filename = 'big.txt'
    # 51 MB
    upload.read.return_value = b'x' * (51 * 1024 * 1024)
    with pytest.raises(FileSizeLimitError):
        await add_file(str(job.id), uid, upload, db)


@pytest.mark.anyio
async def test_add_file_saves_to_disk(tmp_path: Path) -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.DRAFT, user_id=uid)
    db = _db_returning(job)
    db.add = MagicMock()

    upload = AsyncMock()
    upload.filename = 'test.txt'
    upload.read.return_value = b'hello world'

    with patch('app.services.job_service.settings') as mock_settings:
        mock_settings.storage_path = str(tmp_path)
        mock_settings.max_files_per_job = 100
        mock_settings.max_file_size_mb = 50
        await add_file(str(job.id), uid, upload, db)

    expected = tmp_path / str(job.id) / 'test.txt'
    assert expected.exists()
    assert expected.read_bytes() == b'hello world'


@pytest.mark.anyio
async def test_run_job_non_draft_raises() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.PENDING, user_id=uid)
    db = _db_returning(job)
    with pytest.raises(JobStateError):
        await run_job(str(job.id), uid, db)


@pytest.mark.anyio
async def test_run_job_no_files_raises() -> None:
    uid = str(uuid.uuid4())
    job = _job(JobStatus.DRAFT, user_id=uid, files=[])
    db = _db_returning(job)
    with pytest.raises(JobStateError):
        await run_job(str(job.id), uid, db)


@pytest.mark.anyio
async def test_run_job_dispatches_celery_task() -> None:
    uid = str(uuid.uuid4())
    file = MagicMock(spec=JobFile)
    file.file_type = FileType.TEXT
    file.file_size_bytes = 2000
    file.duration_seconds = None
    job = _job(JobStatus.DRAFT, user_id=uid, files=[file])
    db = _db_returning(job)
    db.add = MagicMock()

    mock_task = MagicMock()
    with (
        patch('app.services.billing_service.hold', new=AsyncMock()),
        patch('app.services.billing_service.get_wallet', new=AsyncMock()),
        patch('app.services.job_service.billing_service.hold', new=AsyncMock()),
        patch('app.tasks.pipeline_runner.run_pipeline') as mock_run,
    ):
        mock_run.apply_async = MagicMock()
        with patch('app.services.job_service.billing_service') as mock_billing:
            mock_billing.hold = AsyncMock()

            # patch the deferred import inside run_job
            with patch.dict(
                'sys.modules',
                {'app.tasks.pipeline_runner': MagicMock(run_pipeline=mock_task)},
            ):
                mock_task.apply_async = MagicMock()
                returned_job, credits = await run_job(str(job.id), uid, db)

    assert returned_job.status == JobStatus.PENDING
    assert credits >= Decimal('1')
