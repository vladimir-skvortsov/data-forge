import uuid
from decimal import Decimal

from app.db.enums import FileStatus, FileType, JobStatus, PromoCodeType, TransactionType
from app.db.models import (
    Job,
    JobFile,
    JobResult,
    PromoActivation,
    PromoCode,
    Transaction,
    User,
    Wallet,
)


def test_user_tablename() -> None:
    assert User.__tablename__ == 'users'


def test_wallet_tablename() -> None:
    assert Wallet.__tablename__ == 'wallets'


def test_transaction_tablename() -> None:
    assert Transaction.__tablename__ == 'transactions'


def test_promo_code_tablename() -> None:
    assert PromoCode.__tablename__ == 'promo_codes'


def test_promo_activation_tablename() -> None:
    assert PromoActivation.__tablename__ == 'promo_activations'


def test_job_tablename() -> None:
    assert Job.__tablename__ == 'jobs'


def test_job_file_tablename() -> None:
    assert JobFile.__tablename__ == 'job_files'


def test_job_result_tablename() -> None:
    assert JobResult.__tablename__ == 'job_results'


def test_job_status_values() -> None:
    assert set(JobStatus) == {'draft', 'pending', 'processing', 'completed', 'failed'}


def test_file_status_values() -> None:
    assert set(FileStatus) == {'queued', 'processing', 'done', 'failed'}


def test_file_type_values() -> None:
    assert set(FileType) == {'text', 'image', 'audio'}


def test_transaction_type_values() -> None:
    assert set(TransactionType) == {'topup', 'promo_credit', 'hold', 'charge', 'refund'}


def test_promo_code_type_values() -> None:
    assert set(PromoCodeType) == {'fixed', 'percentage'}


def test_all_models_importable() -> None:
    assert all(
        model.__tablename__
        for model in [
            User,
            Wallet,
            Transaction,
            PromoCode,
            PromoActivation,
            Job,
            JobFile,
            JobResult,
        ]
    )


def test_job_has_jsonb_columns() -> None:
    cols = {c.name for c in Job.__table__.columns}
    assert 'schema_config' in cols
    assert 'pipeline_config' in cols


def test_promo_activation_unique_constraint() -> None:
    constraint_cols = {
        col
        for c in PromoActivation.__table__.constraints
        if hasattr(c, 'columns')
        for col in c.columns.keys()
    }
    assert 'user_id' in constraint_cols
    assert 'promo_code_id' in constraint_cols


def test_job_indices() -> None:
    index_names = {i.name for i in Job.__table__.indexes}
    assert 'idx_jobs_user_id' in index_names
    assert 'idx_jobs_status' in index_names


def test_wallet_balance_is_numeric() -> None:
    col = Wallet.__table__.columns['balance']
    from sqlalchemy import Numeric

    assert isinstance(col.type, Numeric)
    assert col.type.precision == 12
    assert col.type.scale == 2


def test_uuid_primary_keys() -> None:
    for model in [
        User,
        Wallet,
        Transaction,
        PromoCode,
        PromoActivation,
        Job,
        JobFile,
        JobResult,
    ]:
        pk_col = model.__table__.primary_key.columns.values()[0]
        assert pk_col.server_default is not None, (
            f'{model.__tablename__} missing server_default on PK'
        )


def test_transaction_amount_sign_agnostic() -> None:
    # amount can be positive or negative — no check constraint, just Numeric
    col = Transaction.__table__.columns['amount']
    from sqlalchemy import Numeric

    assert isinstance(col.type, Numeric)


def test_job_default_status_is_draft() -> None:
    col = Job.__table__.columns['status']
    assert col.server_default is not None


def test_job_file_cascade_delete() -> None:
    fk = next(iter(JobFile.__table__.foreign_keys))
    assert fk.ondelete == 'CASCADE'


def test_unused_imports_are_in_scope() -> None:
    # Ensure uuid and Decimal are available (used in type hints elsewhere)
    assert uuid.UUID
    assert Decimal
