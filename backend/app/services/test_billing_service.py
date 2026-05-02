import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.enums import PromoCodeType, TransactionType
from app.db.models.promo_code import PromoCode
from app.db.models.transaction import Transaction
from app.db.models.wallet import Wallet
from app.services.billing_service import (
    InsufficientBalanceError,
    PromoAlreadyActivatedError,
    PromoCodeExhaustedError,
    PromoCodeExpiredError,
    PromoCodeInactiveError,
    PromoCodeNotFoundError,
    activate_promo,
    hold,
    refund,
    topup,
)


def _wallet(balance: Decimal = Decimal('100.00')) -> Wallet:
    w = MagicMock(spec=Wallet)
    w.id = uuid.uuid4()
    w.user_id = uuid.uuid4()
    w.balance = balance
    return w


def _promo(
    *,
    code: str = 'TEST10',
    ptype: PromoCodeType = PromoCodeType.FIXED,
    credit_amount: Decimal = Decimal('10.00'),
    is_active: bool = True,
    expires_at: datetime | None = None,
    max_activations: int | None = None,
    current_activations: int = 0,
) -> PromoCode:
    p = MagicMock(spec=PromoCode)
    p.id = uuid.uuid4()
    p.code = code
    p.type = ptype
    p.credit_amount = credit_amount
    p.discount_percentage = None
    p.is_active = is_active
    p.expires_at = expires_at
    p.max_activations = max_activations
    p.current_activations = current_activations
    return p


def _db_with_wallet(wallet: Wallet) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = wallet
    db.execute.return_value = result
    return db


@pytest.mark.anyio
async def test_topup_increases_balance() -> None:
    wallet = _wallet(Decimal('50.00'))
    db = _db_with_wallet(wallet)

    await topup(str(wallet.user_id), Decimal('30.00'), db)

    assert wallet.balance == Decimal('80.00')
    db.add.assert_called()
    db.flush.assert_called()


@pytest.mark.anyio
async def test_topup_creates_topup_transaction() -> None:
    wallet = _wallet()
    db = _db_with_wallet(wallet)

    await topup(str(wallet.user_id), Decimal('25.00'), db)

    added: Transaction = db.add.call_args[0][0]
    assert added.type == TransactionType.TOPUP
    assert added.amount == Decimal('25.00')


@pytest.mark.anyio
async def test_hold_decreases_balance() -> None:
    wallet = _wallet(Decimal('100.00'))
    db = _db_with_wallet(wallet)

    await hold(str(wallet.user_id), str(uuid.uuid4()), Decimal('40.00'), db)

    assert wallet.balance == Decimal('60.00')


@pytest.mark.anyio
async def test_hold_insufficient_balance_raises() -> None:
    wallet = _wallet(Decimal('10.00'))
    db = _db_with_wallet(wallet)

    with pytest.raises(InsufficientBalanceError):
        await hold(str(wallet.user_id), str(uuid.uuid4()), Decimal('50.00'), db)

    assert wallet.balance == Decimal('10.00')  # unchanged


@pytest.mark.anyio
async def test_hold_creates_hold_transaction() -> None:
    wallet = _wallet(Decimal('100.00'))
    db = _db_with_wallet(wallet)
    job_id = str(uuid.uuid4())

    await hold(str(wallet.user_id), job_id, Decimal('15.00'), db)

    added: Transaction = db.add.call_args[0][0]
    assert added.type == TransactionType.HOLD
    assert added.amount == Decimal('-15.00')


@pytest.mark.anyio
async def test_refund_increases_balance() -> None:
    wallet = _wallet(Decimal('30.00'))
    db = _db_with_wallet(wallet)

    await refund(str(wallet.user_id), str(uuid.uuid4()), Decimal('20.00'), db)

    assert wallet.balance == Decimal('50.00')


@pytest.mark.anyio
async def test_refund_creates_refund_transaction() -> None:
    wallet = _wallet()
    db = _db_with_wallet(wallet)

    await refund(str(wallet.user_id), str(uuid.uuid4()), Decimal('5.00'), db)

    added: Transaction = db.add.call_args[0][0]
    assert added.type == TransactionType.REFUND
    assert added.amount == Decimal('5.00')


@pytest.mark.anyio
async def test_promo_fixed_credits_added_to_balance() -> None:
    promo = _promo(credit_amount=Decimal('50.00'))
    wallet = _wallet(Decimal('10.00'))
    db = AsyncMock()
    db.add = MagicMock()

    call_count = 0

    async def _execute(query: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        result.scalar_one_or_none.return_value = promo if call_count == 1 else wallet
        return result

    db.execute.side_effect = _execute

    await activate_promo(str(wallet.user_id), promo.code, db)

    assert wallet.balance == Decimal('60.00')


@pytest.mark.anyio
async def test_promo_not_found_raises() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    with pytest.raises(PromoCodeNotFoundError):
        await activate_promo('user-1', 'NOSUCHCODE', db)


@pytest.mark.anyio
async def test_promo_inactive_raises() -> None:
    promo = _promo(is_active=False)
    db = _db_with_wallet(promo)  # re-use helper — db returns promo from execute
    db.execute.return_value.scalar_one_or_none.return_value = promo

    with pytest.raises(PromoCodeInactiveError):
        await activate_promo('user-1', promo.code, db)


@pytest.mark.anyio
async def test_promo_expired_raises() -> None:
    promo = _promo(expires_at=datetime.now(UTC) - timedelta(days=1))
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = promo
    db.execute.return_value = result

    with pytest.raises(PromoCodeExpiredError):
        await activate_promo('user-1', promo.code, db)


@pytest.mark.anyio
async def test_promo_exhausted_raises() -> None:
    promo = _promo(max_activations=5, current_activations=5)
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = promo
    db.execute.return_value = result

    with pytest.raises(PromoCodeExhaustedError):
        await activate_promo('user-1', promo.code, db)


@pytest.mark.anyio
async def test_promo_duplicate_activation_raises() -> None:
    from sqlalchemy.exc import IntegrityError

    promo = _promo()
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = promo
    db.execute.return_value = result
    db.flush.side_effect = IntegrityError(None, None, Exception('unique'))

    with pytest.raises(PromoAlreadyActivatedError):
        await activate_promo('user-1', promo.code, db)
