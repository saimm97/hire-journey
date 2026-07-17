"""remove profile, project membership, and job note fields

Revision ID: e47c2a9d5f10
Revises: d19f4a8b27c1
Create Date: 2026-07-17 23:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e47c2a9d5f10"
down_revision: Union[str, None] = "d19f4a8b27c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("job_notes")
    op.drop_column("profile_projects", "contribution_summary")
    op.drop_column("profile_projects", "role")
    op.drop_column("profiles", "salary_period")
    op.drop_column("profiles", "salary_currency")


def downgrade() -> None:
    op.add_column("profiles", sa.Column("salary_currency", sa.String(length=3), nullable=True))
    op.add_column("profiles", sa.Column("salary_period", sa.String(length=20), nullable=True))
    op.add_column("profile_projects", sa.Column("role", sa.String(length=255), nullable=True))
    op.add_column(
        "profile_projects",
        sa.Column("contribution_summary", sa.Text(), nullable=True),
    )
    op.create_table(
        "job_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
