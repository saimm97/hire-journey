"""enforce lowercase technology names

Revision ID: d19f4a8b27c1
Revises: c8432c091829
Create Date: 2026-07-17 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d19f4a8b27c1"
down_revision: Union[str, None] = "c8432c091829"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _merge_case_only_duplicates(bridge_table: str, owner_column: str) -> None:
    """Move bridge rows to the lowest technology id for each lowercase name."""
    op.execute(
        f"""
        WITH technology_mapping AS (
            SELECT id AS old_id,
                   min(id) OVER (PARTITION BY lower(name)) AS keep_id
            FROM technologies
        )
        INSERT INTO {bridge_table} ({owner_column}, technology_id)
        SELECT bridge.{owner_column}, mapping.keep_id
        FROM {bridge_table} AS bridge
        JOIN technology_mapping AS mapping
          ON mapping.old_id = bridge.technology_id
        WHERE mapping.old_id <> mapping.keep_id
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        f"""
        WITH technology_mapping AS (
            SELECT id AS old_id,
                   min(id) OVER (PARTITION BY lower(name)) AS keep_id
            FROM technologies
        )
        DELETE FROM {bridge_table} AS bridge
        USING technology_mapping AS mapping
        WHERE bridge.technology_id = mapping.old_id
          AND mapping.old_id <> mapping.keep_id
        """
    )


def upgrade() -> None:
    # Normalizing a case-only duplicate can collide with the unique constraint
    # on technologies.name. Preserve every relationship by repointing both
    # bridge tables to one canonical row before deleting duplicates.
    _merge_case_only_duplicates("profile_technologies", "profile_id")
    _merge_case_only_duplicates("profile_project_technologies", "profile_project_id")

    op.execute(
        """
        WITH technology_mapping AS (
            SELECT id AS old_id,
                   min(id) OVER (PARTITION BY lower(name)) AS keep_id
            FROM technologies
        )
        DELETE FROM technologies AS technology
        USING technology_mapping AS mapping
        WHERE technology.id = mapping.old_id
          AND mapping.old_id <> mapping.keep_id
        """
    )
    op.execute("UPDATE technologies SET name = lower(name) WHERE name <> lower(name)")
    op.create_check_constraint(
        "ck_technologies_name_lowercase",
        "technologies",
        "name = lower(name)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_technologies_name_lowercase",
        "technologies",
        type_="check",
    )
