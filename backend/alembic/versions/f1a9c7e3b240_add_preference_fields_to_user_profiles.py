"""add portfolio_url, minimum_salary, desired_role to user_profiles

Revision ID: f1a9c7e3b240
Revises: d8b3a05f1c62
Create Date: 2026-06-23 13:05:52.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f1a9c7e3b240'
down_revision: Union[str, None] = 'd8b3a05f1c62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("portfolio_url", sa.String(length=255), nullable=True))
    op.add_column("user_profiles", sa.Column("minimum_salary", sa.Integer(), nullable=True))
    op.add_column(
        "user_profiles",
        sa.Column(
            "desired_role",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "desired_role")
    op.drop_column("user_profiles", "minimum_salary")
    op.drop_column("user_profiles", "portfolio_url")
