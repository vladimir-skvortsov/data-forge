from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import settings

_TOKEN_TYPE_ACCESS = 'access'
_TOKEN_TYPE_REFRESH = 'refresh'


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    return _encode({'sub': user_id, 'type': _TOKEN_TYPE_ACCESS, 'exp': expire})


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    return _encode({'sub': user_id, 'type': _TOKEN_TYPE_REFRESH, 'exp': expire})


def decode_access_token(token: str) -> str:
    return _decode_token(token, expected_type=_TOKEN_TYPE_ACCESS)


def decode_refresh_token(token: str) -> str:
    return _decode_token(token, expected_type=_TOKEN_TYPE_REFRESH)


def _encode(payload: dict) -> str:  # type: ignore[type-arg]
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def _decode_token(token: str, expected_type: str) -> str:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError('Invalid token') from exc

    user_id: str | None = payload.get('sub')
    token_type: str | None = payload.get('type')

    if not user_id or token_type != expected_type:
        raise ValueError('Invalid token claims')

    return user_id
