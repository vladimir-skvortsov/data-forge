import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db.enums import FileStatus, FileType, JobStatus
from app.db.models.job import Job
from app.db.models.job_file import JobFile
from app.db.models.user import User
from app.main import app
from app.services.billing_service import InsufficientBalanceError
from app.services.job_service import (
    JobAccessDeniedError,
    JobNotFoundError,
    JobStateError,
)

settings.jwt_secret_key = 'test-secret'


def _make_user() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = 'user@example.com'
    user.created_at = datetime.now(UTC)
    return user


def _make_job(status: JobStatus = JobStatus.DRAFT) -> Job:
    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.title = 'Test Job'
    job.status = status
    job.schema_config = {}
    job.pipeline_config = []
    job.credits_estimate = None
    job.credits_charged = None
    job.error_message = None
    job.created_at = datetime.now(UTC)
    job.updated_at = datetime.now(UTC)
    job.completed_at = None
    job.files = []
    return job


def _make_file() -> JobFile:
    f = MagicMock(spec=JobFile)
    f.id = uuid.uuid4()
    f.original_name = 'test.txt'
    f.file_type = FileType.TEXT
    f.status = FileStatus.QUEUED
    f.file_size_bytes = 1024
    f.created_at = datetime.now(UTC)
    return f


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def override_db() -> Generator[None, None, None]:
    mock_session = AsyncMock()
    app.dependency_overrides[
        __import__('app.db.session', fromlist=['get_db']).get_db
    ] = lambda: mock_session
    yield
    app.dependency_overrides.clear()


def _auth_headers(user: User) -> dict[str, str]:
    from app.core.security import create_access_token

    return {'Authorization': f'Bearer {create_access_token(str(user.id))}'}


@pytest.mark.anyio
async def test_create_job(client: AsyncClient) -> None:
    user = _make_user()
    job = _make_job()

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.create_job', new=AsyncMock(return_value=job)
        ),
    ):
        resp = await client.post(
            '/api/v1/jobs',
            json={'title': 'Test', 'schema_config': {}, 'pipeline_config': []},
            headers=_auth_headers(user),
        )

    assert resp.status_code == 201
    assert resp.json()['status'] == JobStatus.DRAFT.value


@pytest.mark.anyio
async def test_create_job_empty_title_rejected(client: AsyncClient) -> None:
    user = _make_user()
    with patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)):
        resp = await client.post(
            '/api/v1/jobs',
            json={'title': '', 'schema_config': {}},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_jobs(client: AsyncClient) -> None:
    user = _make_user()
    jobs = [_make_job(), _make_job()]

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.list_jobs', new=AsyncMock(return_value=jobs)
        ),
    ):
        resp = await client.get('/api/v1/jobs', headers=_auth_headers(user))

    assert resp.status_code == 200
    assert resp.json()['total'] == 2


@pytest.mark.anyio
async def test_get_job_found(client: AsyncClient) -> None:
    user = _make_user()
    job = _make_job()

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch('app.api.v1.jobs.job_service.get_job', new=AsyncMock(return_value=job)),
    ):
        resp = await client.get(f'/api/v1/jobs/{job.id}', headers=_auth_headers(user))

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_get_job_not_found(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.get_job',
            new=AsyncMock(side_effect=JobNotFoundError),
        ),
    ):
        resp = await client.get(
            f'/api/v1/jobs/{uuid.uuid4()}', headers=_auth_headers(user)
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_job_forbidden(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.get_job',
            new=AsyncMock(side_effect=JobAccessDeniedError),
        ),
    ):
        resp = await client.get(
            f'/api/v1/jobs/{uuid.uuid4()}', headers=_auth_headers(user)
        )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_delete_job_ok(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch('app.api.v1.jobs.job_service.delete_job', new=AsyncMock()),
    ):
        resp = await client.delete(
            f'/api/v1/jobs/{uuid.uuid4()}', headers=_auth_headers(user)
        )
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_delete_job_conflict(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.delete_job',
            new=AsyncMock(side_effect=JobStateError('running')),
        ),
    ):
        resp = await client.delete(
            f'/api/v1/jobs/{uuid.uuid4()}', headers=_auth_headers(user)
        )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_run_job_success(client: AsyncClient) -> None:
    user = _make_user()
    job = _make_job(JobStatus.PENDING)

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.run_job',
            new=AsyncMock(return_value=(job, Decimal('5'))),
        ),
    ):
        resp = await client.post(
            f'/api/v1/jobs/{job.id}/run', headers=_auth_headers(user)
        )

    assert resp.status_code == 200
    assert resp.json()['credits_held'] == '5'


@pytest.mark.anyio
async def test_run_job_insufficient_balance(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.run_job',
            new=AsyncMock(side_effect=InsufficientBalanceError),
        ),
    ):
        resp = await client.post(
            f'/api/v1/jobs/{uuid.uuid4()}/run', headers=_auth_headers(user)
        )
    assert resp.status_code == 402


@pytest.mark.anyio
async def test_run_job_no_files_conflict(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.run_job',
            new=AsyncMock(side_effect=JobStateError('no files')),
        ),
    ):
        resp = await client.post(
            f'/api/v1/jobs/{uuid.uuid4()}/run', headers=_auth_headers(user)
        )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_jobs_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get('/api/v1/jobs')
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_get_job_result_ok(client: AsyncClient) -> None:
    user = _make_user()
    result_data = [{'file': 'doc.txt', 'structured': {'name': 'Alice'}}]

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.get_job_result',
            new=AsyncMock(return_value=result_data),
        ),
    ):
        resp = await client.get(
            f'/api/v1/jobs/{uuid.uuid4()}/result', headers=_auth_headers(user)
        )

    assert resp.status_code == 200
    assert resp.json() == result_data


@pytest.mark.anyio
async def test_get_job_result_not_completed(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.jobs.job_service.get_job_result',
            new=AsyncMock(side_effect=JobStateError('Job is not completed')),
        ),
    ):
        resp = await client.get(
            f'/api/v1/jobs/{uuid.uuid4()}/result', headers=_auth_headers(user)
        )
    assert resp.status_code == 409
