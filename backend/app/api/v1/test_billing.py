import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db.enums import TransactionType
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.db.models.wallet import Wallet
from app.main import app
from app.services.billing_service import (
    PromoAlreadyActivatedError,
    PromoCodeExpiredError,
    PromoCodeNotFoundError,
)

settings.jwt_secret_key = 'test-secret'


def _make_user() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = 'user@example.com'
    user.password_hash = 'hashed'
    user.created_at = datetime.now(UTC)
    return user


def _make_wallet(balance: Decimal = Decimal('100.00')) -> Wallet:
    w = MagicMock(spec=Wallet)
    w.id = uuid.uuid4()
    w.user_id = uuid.uuid4()
    w.balance = balance
    return w


def _make_tx(
    tx_type: TransactionType = TransactionType.TOPUP, amount: Decimal = Decimal('50.00')
) -> Transaction:
    tx = MagicMock(spec=Transaction)
    tx.id = uuid.uuid4()
    tx.type = tx_type
    tx.amount = amount
    tx.description = 'test'
    tx.created_at = datetime.now(UTC)
    return tx


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
async def test_get_balance(client: AsyncClient) -> None:
    user = _make_user()
    wallet = _make_wallet(Decimal('250.00'))

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.get_wallet',
            new=AsyncMock(return_value=wallet),
        ),
    ):
        resp = await client.get('/api/v1/billing/balance', headers=_auth_headers(user))

    assert resp.status_code == 200
    data = resp.json()
    assert data['balance'] == '250.00'
    assert 'wallet_id' in data


@pytest.mark.anyio
async def test_get_balance_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get('/api/v1/billing/balance')
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_topup_success(client: AsyncClient) -> None:
    user = _make_user()
    tx = _make_tx(TransactionType.TOPUP, Decimal('50.00'))

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.topup', new=AsyncMock(return_value=tx)
        ),
    ):
        resp = await client.post(
            '/api/v1/billing/topup',
            json={'amount': '50.00'},
            headers=_auth_headers(user),
        )

    assert resp.status_code == 201
    assert resp.json()['type'] == TransactionType.TOPUP.value


@pytest.mark.anyio
async def test_topup_zero_amount_rejected(client: AsyncClient) -> None:
    user = _make_user()
    with patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)):
        resp = await client.post(
            '/api/v1/billing/topup',
            json={'amount': '0'},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_topup_negative_amount_rejected(client: AsyncClient) -> None:
    user = _make_user()
    with patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)):
        resp = await client.post(
            '/api/v1/billing/topup',
            json={'amount': '-10'},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_activate_promo_success(client: AsyncClient) -> None:
    user = _make_user()
    tx = _make_tx(TransactionType.PROMO_CREDIT, Decimal('10.00'))

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.activate_promo',
            new=AsyncMock(return_value=tx),
        ),
    ):
        resp = await client.post(
            '/api/v1/billing/promo',
            json={'code': 'SAVE10'},
            headers=_auth_headers(user),
        )

    assert resp.status_code == 201
    assert resp.json()['type'] == TransactionType.PROMO_CREDIT.value


@pytest.mark.anyio
async def test_activate_promo_not_found(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.activate_promo',
            new=AsyncMock(side_effect=PromoCodeNotFoundError),
        ),
    ):
        resp = await client.post(
            '/api/v1/billing/promo',
            json={'code': 'NOSUCH'},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_activate_promo_expired(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.activate_promo',
            new=AsyncMock(side_effect=PromoCodeExpiredError),
        ),
    ):
        resp = await client.post(
            '/api/v1/billing/promo',
            json={'code': 'EXPIRED'},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_activate_promo_already_used(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.activate_promo',
            new=AsyncMock(side_effect=PromoAlreadyActivatedError),
        ),
    ):
        resp = await client.post(
            '/api/v1/billing/promo',
            json={'code': 'USED'},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 409


@pytest.mark.anyio
async def test_list_transactions(client: AsyncClient) -> None:
    user = _make_user()
    txs = [
        _make_tx(TransactionType.TOPUP, Decimal('100.00')),
        _make_tx(TransactionType.HOLD, Decimal('-20.00')),
    ]

    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.get_transactions',
            new=AsyncMock(return_value=txs),
        ),
    ):
        resp = await client.get(
            '/api/v1/billing/transactions', headers=_auth_headers(user)
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 2
    assert len(data['items']) == 2


@pytest.mark.anyio
async def test_list_transactions_empty(client: AsyncClient) -> None:
    user = _make_user()
    with (
        patch('app.api.deps.auth_service.get_by_id', new=AsyncMock(return_value=user)),
        patch(
            'app.api.v1.billing.billing_service.get_transactions',
            new=AsyncMock(return_value=[]),
        ),
    ):
        resp = await client.get(
            '/api/v1/billing/transactions', headers=_auth_headers(user)
        )

    assert resp.status_code == 200
    assert resp.json() == {'items': [], 'total': 0}
