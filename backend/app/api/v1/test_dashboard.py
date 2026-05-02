from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db.models.user import User
from app.main import app

settings.jwt_secret_key = 'test-secret'


def _make_user() -> User:
    from datetime import UTC, datetime

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = 'user@example.com'
    user.created_at = datetime.now(UTC)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    from app.core.security import create_access_token

    token = create_access_token(str(user.id))
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_get_stats_ok(client: AsyncClient) -> None:
    user = _make_user()
    stats = {
        'jobs_by_status': {'draft': 2, 'completed': 5},
        'credits_by_day': [{'date': '2026-05-01', 'credits': 10.0}],
        'top_file_types': [{'file_type': 'text', 'count': 7}],
        'total_credits_spent': Decimal('25.00'),
    }

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.services.dashboard_service.get_stats',
            new_callable=AsyncMock,
            return_value=stats,
        ),
    ):
        resp = await client.get('/api/v1/dashboard/stats', headers=_auth_headers(user))

    assert resp.status_code == 200
    body = resp.json()
    assert body['jobs_by_status']['draft'] == 2
    assert body['total_credits_spent'] == '25.00'


@pytest.mark.anyio
async def test_get_stats_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get('/api/v1/dashboard/stats')
    assert resp.status_code == 401
