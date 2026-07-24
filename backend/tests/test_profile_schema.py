"""Focused tests for the onboarding profile schema and normalization rules."""

from app.database import Base
from app.models import (
    EmploymentHistory,
    Profile,
    ProfileProject,
    ProfileProjectTechnology,
    ProfileTechnology,
    Project,
    Technology,
)
from app.schemas.profile import ProfileUpdate
from app.services.profile_service import normalize_technology


def test_profile_update_normalizes_nullable_arrays():
    update = ProfileUpdate.model_validate(
        {
            "desired_roles": None,
            "work_modes_preferred": ["remote"],
        }
    )

    assert update.desired_roles == []
    assert update.work_modes_preferred == ["remote"]


def test_technology_normalization_is_case_and_whitespace_insensitive():
    assert normalize_technology("  PostgreSQL  ") == "postgresql"
    assert normalize_technology("Node   JS") == "node js"


def test_technology_model_normalizes_name_and_declares_database_constraint():
    technology = Technology(name="  PyThOn  ")
    constraint_names = {constraint.name for constraint in Technology.__table__.constraints}

    assert technology.name == "python"
    assert "ck_technologies_name_lowercase" in constraint_names


def test_onboarding_tables_are_registered_with_expected_names():
    assert Profile.__tablename__ == "profiles"
    assert Project.__tablename__ == "projects"
    assert ProfileProject.__tablename__ == "profile_projects"
    assert EmploymentHistory.__tablename__ == "employment_history"
    assert Technology.__tablename__ == "technologies"
    assert ProfileTechnology.__tablename__ == "profile_technologies"
    assert ProfileProjectTechnology.__tablename__ == "profile_project_technologies"


def test_removed_profile_and_project_fields_are_not_in_metadata():
    assert {"salary_currency", "salary_period"}.isdisjoint(Profile.__table__.columns.keys())
    assert {"role", "contribution_summary"}.isdisjoint(ProfileProject.__table__.columns.keys())
    assert "job_notes" not in Base.metadata.tables
    assert "applications" not in Base.metadata.tables
