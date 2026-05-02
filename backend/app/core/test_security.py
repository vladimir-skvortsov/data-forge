from datetime import UTC, datetime, timedelta

import pytest

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)

settings.jwt_secret_key = 'test-secret-key'


def test_hash_password_returns_non_empty_string() -> None:
    result = hash_password('mypassword')
    assert isinstance(result, str)
    assert len(result) > 0


def test_hash_password_is_not_plaintext() -> None:
    assert hash_password('mypassword') != 'mypassword'


def test_verify_password_correct() -> None:
    hashed = hash_password('correct')
    assert verify_password('correct', hashed) is True


def test_verify_password_wrong() -> None:
    hashed = hash_password('correct')
    assert verify_password('wrong', hashed) is False


def test_create_access_token_is_string() -> None:
    assert isinstance(create_access_token('user-123'), str)


def test_decode_access_token_returns_user_id() -> None:
    token = create_access_token('user-abc')
    assert decode_access_token(token) == 'user-abc'


def test_decode_refresh_token_returns_user_id() -> None:
    token = create_refresh_token('user-xyz')
    assert decode_refresh_token(token) == 'user-xyz'


def test_access_token_rejected_as_refresh() -> None:
    token = create_access_token('user-1')
    with pytest.raises(ValueError, match='Invalid token claims'):
        decode_refresh_token(token)


def test_refresh_token_rejected_as_access() -> None:
    token = create_refresh_token('user-1')
    with pytest.raises(ValueError, match='Invalid token claims'):
        decode_access_token(token)


def test_invalid_token_raises_value_error() -> None:
    with pytest.raises(ValueError, match='Invalid token'):
        decode_access_token('not.a.token')


def test_expired_token_raises_value_error() -> None:
    from jose import jwt

    expired_payload = {
        'sub': 'user-1',
        'type': 'access',
        'exp': datetime.now(UTC) - timedelta(seconds=1),
    }
    token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(ValueError, match='Invalid token'):
        decode_access_token(token)
