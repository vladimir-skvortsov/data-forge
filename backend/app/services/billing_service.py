from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PromoCodeType, TransactionType
from app.db.models.promo_activation import PromoActivation
from app.db.models.promo_code import PromoCode
from app.db.models.transaction import Transaction
from app.db.models.wallet import Wallet


class InsufficientBalanceError(Exception):
    pass


class PromoCodeNotFoundError(Exception):
    pass


class PromoCodeExpiredError(Exception):
    pass


class PromoCodeInactiveError(Exception):
    pass


class PromoCodeExhaustedError(Exception):
    pass


class PromoAlreadyActivatedError(Exception):
    pass


async def get_balance(user_id: str, db: AsyncSession) -> Decimal:
    result = await db.execute(select(Wallet.balance).where(Wallet.user_id == user_id))
    return result.scalar_one_or_none() or Decimal('0')


async def get_wallet(user_id: str, db: AsyncSession) -> Wallet:
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        msg = f'Wallet not found for user {user_id}'
        raise ValueError(msg)
    return wallet


async def topup(user_id: str, amount: Decimal, db: AsyncSession) -> Transaction:
    wallet = await get_wallet(user_id, db)
    wallet.balance += amount

    tx = Transaction(
        user_id=wallet.user_id,
        type=TransactionType.TOPUP,
        amount=amount,
        description=f'Top-up {amount} credits',
    )
    db.add(tx)
    await db.flush()
    return tx


async def hold(
    user_id: str, job_id: str, amount: Decimal, db: AsyncSession
) -> Transaction:
    wallet = await get_wallet(user_id, db)

    if wallet.balance < amount:
        raise InsufficientBalanceError(f'Balance {wallet.balance} < {amount}')

    wallet.balance -= amount

    tx = Transaction(
        user_id=wallet.user_id,
        job_id=job_id,
        type=TransactionType.HOLD,
        amount=-amount,
        description=f'Hold {amount} credits for job {job_id}',
    )
    db.add(tx)
    await db.flush()
    return tx


async def charge(
    user_id: str,
    job_id: str,
    actual_amount: Decimal,
    held_amount: Decimal,
    db: AsyncSession,
) -> None:
    tx = Transaction(
        user_id=user_id,
        job_id=job_id,
        type=TransactionType.CHARGE,
        amount=-actual_amount,
        description=f'Charge {actual_amount} credits for job {job_id}',
    )
    db.add(tx)

    # Refund unused portion of the hold
    unused = held_amount - actual_amount
    if unused > 0:
        await refund(
            user_id,
            job_id,
            unused,
            db,
            description=f'Partial refund {unused} credits for job {job_id}',
        )
    else:
        await db.flush()


async def refund(
    user_id: str,
    job_id: str,
    amount: Decimal,
    db: AsyncSession,
    description: str | None = None,
) -> Transaction:
    wallet = await get_wallet(user_id, db)
    wallet.balance += amount

    tx = Transaction(
        user_id=wallet.user_id,
        job_id=job_id,
        type=TransactionType.REFUND,
        amount=amount,
        description=description or f'Refund {amount} credits for job {job_id}',
    )
    db.add(tx)
    await db.flush()
    return tx


async def activate_promo(user_id: str, code: str, db: AsyncSession) -> Transaction:
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == code).with_for_update()
    )
    promo = result.scalar_one_or_none()

    if promo is None:
        raise PromoCodeNotFoundError(code)
    if not promo.is_active:
        raise PromoCodeInactiveError(code)
    if promo.expires_at and promo.expires_at < datetime.now(UTC):
        raise PromoCodeExpiredError(code)
    if (
        promo.max_activations is not None
        and promo.current_activations >= promo.max_activations
    ):
        raise PromoCodeExhaustedError(code)

    activation = PromoActivation(user_id=user_id, promo_code_id=promo.id)
    db.add(activation)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise PromoAlreadyActivatedError(code) from exc

    promo.current_activations += 1

    if promo.type == PromoCodeType.FIXED and promo.credit_amount:
        amount = promo.credit_amount
        wallet = await get_wallet(user_id, db)
        wallet.balance += amount
        tx = Transaction(
            user_id=user_id,
            type=TransactionType.PROMO_CREDIT,
            amount=amount,
            description=f'Promo code {code}: +{amount} credits',
        )
        db.add(tx)
        await db.flush()
        return tx

    # percentage type: return a placeholder transaction (discount applied at next topup)
    tx = Transaction(
        user_id=user_id,
        type=TransactionType.PROMO_CREDIT,
        amount=Decimal('0'),
        description=f'Promo code {code}: {promo.discount_percentage}% discount applied',
    )
    db.add(tx)
    await db.flush()
    return tx


async def get_transactions(user_id: str, db: AsyncSession) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
    )
    return list(result.scalars().all())
