"""add projects table, slim user_profiles

Revision ID: 2d1a96ec4867
Revises: b5a144df9186
Create Date: 2026-06-22 23:35:25.598300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '2d1a96ec4867'
down_revision: Union[str, None] = 'b5a144df9186'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tech_stack", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("github_url", sa.String(length=255), nullable=True),
        sa.Column("deployed_url", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.drop_column("user_profiles", "summary")
    op.drop_column("user_profiles", "projects_summary")
    op.drop_column("user_profiles", "raw_extraction")


def downgrade() -> None:
    op.add_column("user_profiles", sa.Column("raw_extraction", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("user_profiles", sa.Column("projects_summary", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("summary", sa.Text(), nullable=True))
    op.drop_table("projects")
