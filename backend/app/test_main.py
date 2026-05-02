from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


@pytest.mark.anyio
async def test_health_content_type_is_json(client: AsyncClient) -> None:
    response = await client.get('/health')

    assert 'application/json' in response.headers['content-type']
