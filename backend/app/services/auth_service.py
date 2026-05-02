from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models.user import User
from app.db.models.wallet import Wallet


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register(email: str, password: str, db: AsyncSession) -> User:
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise EmailAlreadyExistsError(email) from exc

    wallet = Wallet(user_id=user.id)
    db.add(wallet)
    await db.flush()

    return user


async def authenticate(email: str, password: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError

    return user


async def get_by_id(user_id: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
