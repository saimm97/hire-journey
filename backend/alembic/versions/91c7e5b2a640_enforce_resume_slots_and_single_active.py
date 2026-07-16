"""enforce two resume slots and one active resume

Revision ID: 91c7e5b2a640
Revises: 6f4a2d9c8b31
Create Date: 2026-07-16 22:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "91c7e5b2a640"
down_revision: Union[str, None] = "6f4a2d9c8b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Never delete user documents implicitly. If legacy data violates the new
    # business rule, fail with a clear remediation message instead.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM resumes
                GROUP BY user_id
                HAVING count(*) > 2
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce resume limit: at least one user has more than two resumes';
            END IF;
        END
        $$
        """
    )

    op.add_column("resumes", sa.Column("slot_number", sa.SmallInteger(), nullable=True))
    op.add_column(
        "resumes",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT resume_id,
                   row_number() OVER (
                       PARTITION BY user_id
                       ORDER BY is_active DESC, created_at DESC, resume_id
                   ) AS slot_number
            FROM resumes
        )
        UPDATE resumes
        SET slot_number = ranked.slot_number
        FROM ranked
        WHERE ranked.resume_id = resumes.resume_id
        """
    )
    # Make the preferred/latest existing resume active and deactivate any other
    # resume, repairing legacy rows before the unique index is created.
    op.execute(
        """
        WITH ranked AS (
            SELECT resume_id,
                   row_number() OVER (
                       PARTITION BY user_id
                       ORDER BY is_active DESC, created_at DESC, resume_id
                   ) AS active_rank
            FROM resumes
        )
        UPDATE resumes
        SET is_active = (ranked.active_rank = 1)
        FROM ranked
        WHERE ranked.resume_id = resumes.resume_id
        """
    )
    op.alter_column("resumes", "slot_number", nullable=False)
    op.create_check_constraint("ck_resumes_slot_number", "resumes", "slot_number IN (1, 2)")
    op.create_unique_constraint("uq_resumes_user_slot", "resumes", ["user_id", "slot_number"])
    op.create_index(
        "uq_resumes_one_active_per_user",
        "resumes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_resumes_one_active_per_user", table_name="resumes")
    op.drop_constraint("uq_resumes_user_slot", "resumes", type_="unique")
    op.drop_constraint("ck_resumes_slot_number", "resumes", type_="check")
    op.drop_column("resumes", "updated_at")
    op.drop_column("resumes", "slot_number")
