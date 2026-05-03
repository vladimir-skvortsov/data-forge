"""job_results_cascade_delete

Revision ID: 9e2b463c873f
Revises: f49e9527c27f
Create Date: 2026-05-03 19:20:29.347127

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9e2b463c873f'
down_revision: Union[str, None] = 'f49e9527c27f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('job_results_job_id_fkey', 'job_results', type_='foreignkey')
    op.create_foreign_key(
        'job_results_job_id_fkey',
        'job_results',
        'jobs',
        ['job_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('job_results_job_id_fkey', 'job_results', type_='foreignkey')
    op.create_foreign_key(
        'job_results_job_id_fkey', 'job_results', 'jobs', ['job_id'], ['id']
    )
