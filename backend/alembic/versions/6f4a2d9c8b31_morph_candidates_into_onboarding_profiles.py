"""morph candidates into onboarding profiles

Revision ID: 6f4a2d9c8b31
Revises: 44db610f1cc8
Create Date: 2026-07-16 20:00:00.000000
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "6f4a2d9c8b31"
down_revision: Union[str, None] = "44db610f1cc8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalized_technology(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def upgrade() -> None:
    # Candidate is the old name for the user's one-to-one onboarding profile.
    op.rename_table("candidates", "profiles")
    op.add_column("profiles", sa.Column("profile_id", sa.UUID(), nullable=True))
    op.execute("UPDATE profiles SET profile_id = user_id")
    op.drop_constraint("user_profiles_pkey", "profiles", type_="primary")
    op.alter_column("profiles", "profile_id", nullable=False)
    op.create_primary_key("pk_profiles", "profiles", ["profile_id"])
    op.create_unique_constraint("uq_profiles_user_id", "profiles", ["user_id"])

    op.alter_column(
        "profiles", "phone", new_column_name="phone_number", existing_type=sa.String(50)
    )
    op.alter_column(
        "profiles",
        "desired_role",
        new_column_name="desired_roles",
        existing_type=postgresql.ARRAY(sa.String()),
        existing_nullable=False,
    )
    op.add_column("profiles", sa.Column("location", sa.String(length=255), nullable=True))
    op.add_column(
        "profiles",
        sa.Column(
            "social_links",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "education",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "certifications",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("profiles", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("profiles", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("salary_currency", sa.String(length=3), nullable=True))
    op.add_column("profiles", sa.Column("salary_period", sa.String(length=20), nullable=True))
    op.add_column(
        "profiles",
        sa.Column(
            "desired_locations",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "work_modes_preferred",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column("profiles", sa.Column("seniority_level", sa.String(length=50), nullable=True))
    op.create_check_constraint(
        "ck_profiles_minimum_salary_nonnegative",
        "profiles",
        "minimum_salary IS NULL OR minimum_salary >= 0",
    )
    op.create_check_constraint(
        "ck_profiles_social_links_object",
        "profiles",
        "jsonb_typeof(social_links) = 'object'",
    )
    op.create_check_constraint(
        "ck_profiles_education_array", "profiles", "jsonb_typeof(education) = 'array'"
    )
    op.create_check_constraint(
        "ck_profiles_certifications_array",
        "profiles",
        "jsonb_typeof(certifications) = 'array'",
    )

    # Retain the URL information that used to be spread across flat columns and
    # the LinkedIn extraction blob.
    op.execute(
        """
        UPDATE profiles
        SET social_links = jsonb_strip_nulls(
            jsonb_build_object(
                'github_url', github_url,
                'portfolio_url', portfolio_url,
                'linkedin_url', linkedin_data ->> 'linkedin_url'
            )
        )
        """
    )

    op.create_table(
        "technologies",
        sa.Column("technology_id", sa.UUID(), nullable=False),
        sa.Column("canonical_name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("technology_id"),
        sa.UniqueConstraint("normalized_name", name="uq_technologies_normalized_name"),
    )
    op.create_table(
        "profile_technologies",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("technology_id", sa.UUID(), nullable=False),
        sa.Column("proficiency", sa.String(length=30), nullable=True),
        sa.Column("years_experience", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.CheckConstraint(
            "years_experience IS NULL OR years_experience >= 0",
            name="ck_profile_technologies_years_nonnegative",
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.profile_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["technology_id"], ["technologies.technology_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("profile_id", "technology_id"),
    )

    # Convert existing candidate string arrays to canonical technology rows.
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT profile_id, tech_stack FROM profiles WHERE tech_stack IS NOT NULL")
    ).mappings()
    technology_rows: dict[str, dict] = {}
    memberships: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for row in existing:
        for raw_name in row["tech_stack"] or []:
            normalized = _normalized_technology(raw_name)
            if not normalized:
                continue
            technology = technology_rows.setdefault(
                normalized,
                {
                    "technology_id": uuid.uuid5(
                        uuid.NAMESPACE_URL, f"hire-journey:technology:{normalized}"
                    ),
                    "canonical_name": " ".join(raw_name.strip().split()),
                    "normalized_name": normalized,
                },
            )
            memberships.add((row["profile_id"], technology["technology_id"]))

    if technology_rows:
        technology_table = sa.table(
            "technologies",
            sa.column("technology_id", sa.UUID()),
            sa.column("canonical_name", sa.String()),
            sa.column("normalized_name", sa.String()),
        )
        op.bulk_insert(technology_table, list(technology_rows.values()))
    if memberships:
        membership_table = sa.table(
            "profile_technologies",
            sa.column("profile_id", sa.UUID()),
            sa.column("technology_id", sa.UUID()),
        )
        op.bulk_insert(
            membership_table,
            [
                {"profile_id": profile_id, "technology_id": technology_id}
                for profile_id, technology_id in sorted(
                    memberships, key=lambda item: (str(item[0]), str(item[1]))
                )
            ],
        )

    op.create_table(
        "profile_projects",
        sa.Column("profile_project_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("contribution_summary", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_profile_projects_dates",
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.profile_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_project_id"),
        sa.UniqueConstraint("profile_id", "project_id", name="uq_profile_projects_pair"),
    )
    op.execute(
        """
        INSERT INTO profile_projects (
            profile_project_id, profile_id, project_id, source, created_at
        )
        SELECT projects.project_id, profiles.profile_id, projects.project_id,
               projects.source, projects.created_at
        FROM projects
        JOIN profiles ON profiles.user_id = projects.user_id
        """
    )
    op.add_column("projects", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column(
        "projects",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.drop_column("projects", "source")
    op.drop_column("projects", "user_id")

    op.create_table(
        "employment_history",
        sa.Column("employment_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("employment_type", sa.String(length=50), nullable=True),
        sa.Column("work_mode", sa.String(length=20), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_employment_history_dates",
        ),
        sa.CheckConstraint(
            "NOT (is_current AND end_date IS NOT NULL)",
            name="ck_employment_history_current_no_end",
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.profile_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("employment_id"),
    )
    op.create_index("ix_employment_history_profile_id", "employment_history", ["profile_id"])

    op.drop_column("profiles", "email")
    op.drop_column("profiles", "github_url")
    op.drop_column("profiles", "portfolio_url")
    op.drop_column("profiles", "linkedin_data")
    op.drop_column("profiles", "tech_stack")


def downgrade() -> None:
    # Downgrading shared projects is inherently lossy: the oldest membership is
    # chosen as the legacy owner because the old schema allowed only one owner.
    op.add_column("profiles", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("profiles", sa.Column("github_url", sa.String(length=255), nullable=True))
    op.add_column("profiles", sa.Column("portfolio_url", sa.String(length=255), nullable=True))
    op.add_column("profiles", sa.Column("linkedin_data", postgresql.JSON(), nullable=True))
    op.add_column("profiles", sa.Column("tech_stack", postgresql.ARRAY(sa.String()), nullable=True))
    op.execute(
        """
        UPDATE profiles
        SET email = users.email,
            github_url = social_links ->> 'github_url',
            portfolio_url = social_links ->> 'portfolio_url',
            linkedin_data = json_build_object('linkedin_url', social_links ->> 'linkedin_url')
        FROM users
        WHERE users.user_id = profiles.user_id
        """
    )
    op.execute(
        """
        UPDATE profiles
        SET tech_stack = technology_list.names
        FROM (
            SELECT pt.profile_id, array_agg(t.canonical_name ORDER BY t.canonical_name) AS names
            FROM profile_technologies pt
            JOIN technologies t ON t.technology_id = pt.technology_id
            GROUP BY pt.profile_id
        ) AS technology_list
        WHERE technology_list.profile_id = profiles.profile_id
        """
    )

    op.add_column("projects", sa.Column("user_id", sa.UUID(), nullable=True))
    op.add_column("projects", sa.Column("source", sa.String(length=20), nullable=True))
    op.execute(
        """
        UPDATE projects
        SET user_id = owner.user_id, source = COALESCE(owner.source, 'cv')
        FROM (
            SELECT DISTINCT ON (pp.project_id)
                   pp.project_id, p.user_id, pp.source
            FROM profile_projects pp
            JOIN profiles p ON p.profile_id = pp.profile_id
            ORDER BY pp.project_id, pp.created_at
        ) AS owner
        WHERE owner.project_id = projects.project_id
        """
    )
    op.execute("DELETE FROM projects WHERE user_id IS NULL")
    op.alter_column("projects", "user_id", nullable=False)
    op.alter_column("projects", "source", nullable=False)
    op.create_foreign_key(
        "fk_projects_user_id_users",
        "projects",
        "users",
        ["user_id"],
        ["user_id"],
        ondelete="CASCADE",
    )
    op.drop_column("projects", "updated_at")
    op.drop_column("projects", "end_date")
    op.drop_column("projects", "start_date")

    op.drop_index("ix_employment_history_profile_id", table_name="employment_history")
    op.drop_table("employment_history")
    op.drop_table("profile_projects")
    op.drop_table("profile_technologies")
    op.drop_table("technologies")

    op.drop_constraint("ck_profiles_certifications_array", "profiles", type_="check")
    op.drop_constraint("ck_profiles_education_array", "profiles", type_="check")
    op.drop_constraint("ck_profiles_social_links_object", "profiles", type_="check")
    op.drop_constraint("ck_profiles_minimum_salary_nonnegative", "profiles", type_="check")
    op.drop_column("profiles", "seniority_level")
    op.drop_column("profiles", "work_modes_preferred")
    op.drop_column("profiles", "desired_locations")
    op.drop_column("profiles", "salary_period")
    op.drop_column("profiles", "salary_currency")
    op.drop_column("profiles", "summary")
    op.drop_column("profiles", "title")
    op.drop_column("profiles", "certifications")
    op.drop_column("profiles", "education")
    op.drop_column("profiles", "social_links")
    op.drop_column("profiles", "location")
    op.alter_column(
        "profiles",
        "desired_roles",
        new_column_name="desired_role",
        existing_type=postgresql.ARRAY(sa.String()),
        existing_nullable=False,
    )
    op.alter_column(
        "profiles",
        "phone_number",
        new_column_name="phone",
        existing_type=sa.String(50),
    )

    op.drop_constraint("pk_profiles", "profiles", type_="primary")
    op.drop_constraint("uq_profiles_user_id", "profiles", type_="unique")
    op.drop_column("profiles", "profile_id")
    op.create_primary_key("user_profiles_pkey", "profiles", ["user_id"])
    op.rename_table("profiles", "candidates")
