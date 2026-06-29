"""drop linkedin_summary from user_profiles

Revision ID: d8b3a05f1c62
Revises: c4e2f8a1b9d7
Create Date: 2026-06-23 12:40:18.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8b3a05f1c62'
down_revision: Union[str, None] = 'c4e2f8a1b9d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("user_profiles", "linkedin_summary")


def downgrade() -> None:
    op.add_column("user_profiles", sa.Column("linkedin_summary", sa.Text(), nullable=True))
