"""add summary to candidates

Revision ID: 1eb491bdc0e1
Revises: cd6098360773
Create Date: 2026-07-07 20:10:09.098503

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = '1eb491bdc0e1'
down_revision: Union[str, None] = 'cd6098360773'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("candidates", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("candidates", "summary")
