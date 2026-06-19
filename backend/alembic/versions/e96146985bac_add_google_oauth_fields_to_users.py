"""add google oauth fields to users

Revision ID: e96146985bac
Revises: 62d0e0cecc81
Create Date: 2026-06-19 23:01:03.495817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e96146985bac'
down_revision: Union[str, None] = '62d0e0cecc81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Google-linked accounts have no local password.
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)
    # Store Google's stable subject id and keep it unique for account linking.
    op.add_column("users", sa.Column("google_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
    op.drop_column("users", "google_id")
    # Note: fails if any password-less (Google-only) users exist.
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
