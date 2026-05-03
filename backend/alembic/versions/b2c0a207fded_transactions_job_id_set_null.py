"""transactions_job_id_set_null

Revision ID: b2c0a207fded
Revises: 9e2b463c873f
Create Date: 2026-05-03 19:22:35.810649

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c0a207fded'
down_revision: Union[str, None] = '9e2b463c873f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('transactions_job_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_job_id_fkey',
        'transactions',
        'jobs',
        ['job_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('transactions_job_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_job_id_fkey', 'transactions', 'jobs', ['job_id'], ['id']
    )
