"""add job-preference fields to candidates, drop linkedin_data

Revision ID: 7c4e9a1f2b60
Revises: 1eb491bdc0e1
Create Date: 2026-07-09 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '7c4e9a1f2b60'
down_revision: Union[str, None] = '1eb491bdc0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column in ("seniority_level", "location"):
        op.add_column(
            "candidates",
            sa.Column(
                column,
                postgresql.ARRAY(sa.String()),
                server_default=sa.text("'{}'"),
                nullable=False,
            ),
        )
    op.add_column("candidates", sa.Column("work_mode", sa.String(length=20), nullable=True))
    op.add_column(
        "candidates",
        sa.Column(
            "open_to_relocating",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.drop_column("candidates", "linkedin_data")


def downgrade() -> None:
    op.add_column("candidates", sa.Column("linkedin_data", postgresql.JSON(), nullable=True))
    op.drop_column("candidates", "open_to_relocating")
    op.drop_column("candidates", "work_mode")
    op.drop_column("candidates", "location")
    op.drop_column("candidates", "seniority_level")
