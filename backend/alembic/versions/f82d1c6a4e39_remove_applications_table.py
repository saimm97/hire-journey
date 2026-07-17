"""remove applications table

Revision ID: f82d1c6a4e39
Revises: e47c2a9d5f10
Create Date: 2026-07-18 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f82d1c6a4e39"
down_revision: Union[str, None] = "e47c2a9d5f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("applications")
    postgresql.ENUM(name="applicationstatus").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    application_status = postgresql.ENUM(
        "saved",
        "applied",
        "interviewing",
        "offered",
        "rejected",
        name="applicationstatus",
    )
    application_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("tailored_resume_id", sa.Integer(), nullable=True),
        sa.Column("status", application_status, nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tailored_resume_id"], ["tailored_resumes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
