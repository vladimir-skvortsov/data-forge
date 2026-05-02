import uuid
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db.models.user import User
from app.main import app
from app.services.auth_service import EmailAlreadyExistsError, InvalidCredentialsError

settings.jwt_secret_key = 'test-secret'


def _make_user(email: str = 'user@example.com') -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = email
    user.password_hash = 'hashed'
    from datetime import UTC, datetime

    user.created_at = datetime.now(UTC)
    return user


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


@pytest.mark.anyio
async def test_register_success(client: AsyncClient) -> None:
    user = _make_user()
    with patch(
        'app.api.v1.auth.auth_service.register', new=AsyncMock(return_value=user)
    ):
        resp = await client.post(
            '/api/v1/auth/register',
            json={'email': 'a@b.com', 'password': 'password123'},
        )

    assert resp.status_code == 201
    assert resp.json()['email'] == user.email


@pytest.mark.anyio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    with patch(
        'app.api.v1.auth.auth_service.register',
        new=AsyncMock(side_effect=EmailAlreadyExistsError),
    ):
        resp = await client.post(
            '/api/v1/auth/register',
            json={'email': 'a@b.com', 'password': 'password123'},
        )

    assert resp.status_code == 409


@pytest.mark.anyio
async def test_register_password_too_short(client: AsyncClient) -> None:
    resp = await client.post(
        '/api/v1/auth/register', json={'email': 'a@b.com', 'password': 'short'}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_login_success(client: AsyncClient) -> None:
    user = _make_user()
    with patch(
        'app.api.v1.auth.auth_service.authenticate', new=AsyncMock(return_value=user)
    ):
        resp = await client.post(
            '/api/v1/auth/login', json={'email': 'a@b.com', 'password': 'password123'}
        )

    assert resp.status_code == 200
    data = resp.json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['token_type'] == 'bearer'


@pytest.mark.anyio
async def test_login_wrong_credentials(client: AsyncClient) -> None:
    with patch(
        'app.api.v1.auth.auth_service.authenticate',
        new=AsyncMock(side_effect=InvalidCredentialsError),
    ):
        resp = await client.post(
            '/api/v1/auth/login', json={'email': 'a@b.com', 'password': 'wrong'}
        )

    assert resp.status_code == 401


@pytest.mark.anyio
async def test_refresh_success(client: AsyncClient) -> None:
    from app.core.security import create_refresh_token

    token = create_refresh_token('user-1')
    resp = await client.post('/api/v1/auth/refresh', json={'refresh_token': token})

    assert resp.status_code == 200
    assert 'access_token' in resp.json()


@pytest.mark.anyio
async def test_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        '/api/v1/auth/refresh', json={'refresh_token': 'bad.token'}
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_me_returns_user(client: AsyncClient) -> None:
    user = _make_user()
    with patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)):
        from app.core.security import create_access_token

        token = create_access_token(str(user.id))
        resp = await client.get(
            '/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'}
        )

    assert resp.status_code == 200
    assert resp.json()['email'] == user.email


@pytest.mark.anyio
async def test_me_without_token(client: AsyncClient) -> None:
    resp = await client.get('/api/v1/auth/me')
    assert resp.status_code == 401
