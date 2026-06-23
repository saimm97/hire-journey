"""rename user_profiles to candidates, drop linkedin_profiles, fold linkedin into json

Revision ID: a72be9410f33
Revises: f1a9c7e3b240
Create Date: 2026-06-23 13:40:09.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a72be9410f33'
down_revision: Union[str, None] = 'f1a9c7e3b240'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("linkedin_profiles")
    op.rename_table("user_profiles", "candidates")
    op.drop_column("candidates", "linkedin_url")
    op.add_column(
        "candidates",
        sa.Column("linkedin_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidates", "linkedin_data")
    op.add_column("candidates", sa.Column("linkedin_url", sa.String(length=255), nullable=True))
    op.rename_table("candidates", "user_profiles")
    op.create_table(
        "linkedin_profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("parsed_content", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
