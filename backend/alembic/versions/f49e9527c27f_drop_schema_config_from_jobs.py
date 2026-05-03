"""drop_schema_config_from_jobs

Revision ID: f49e9527c27f
Revises: 12e6511c16f3
Create Date: 2026-05-03 19:03:39.089928

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f49e9527c27f'
down_revision: Union[str, None] = '12e6511c16f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('jobs', 'schema_config')


def downgrade() -> None:
    op.add_column(
        'jobs',
        sa.Column('schema_config', sa.dialects.postgresql.JSONB(), nullable=True),
    )
