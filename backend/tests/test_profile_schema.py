"""Focused tests for the onboarding profile schema and normalization rules."""

import pytest
from pydantic import ValidationError

from app.models import (
    EmploymentHistory,
    Profile,
    ProfileProject,
    ProfileTechnology,
    Project,
    Technology,
)
from app.schemas.profile import ProfileUpdate, TechnologySelection
from app.services.profile_service import normalize_technology


def test_profile_update_normalizes_currency_and_nullable_arrays():
    update = ProfileUpdate.model_validate(
        {
            "salary_currency": "pkr",
            "desired_roles": None,
            "work_modes_preferred": ["remote"],
        }
    )

    assert update.salary_currency == "PKR"
    assert update.desired_roles == []
    assert update.work_modes_preferred == ["remote"]


def test_technology_selection_requires_id_or_name():
    with pytest.raises(ValidationError):
        TechnologySelection()


def test_technology_normalization_is_case_and_whitespace_insensitive():
    assert normalize_technology("  PostgreSQL  ") == "postgresql"
    assert normalize_technology("Node   JS") == "node js"


def test_onboarding_tables_are_registered_with_expected_names():
    assert Profile.__tablename__ == "profiles"
    assert Project.__tablename__ == "projects"
    assert ProfileProject.__tablename__ == "profile_projects"
    assert EmploymentHistory.__tablename__ == "employment_history"
    assert Technology.__tablename__ == "technologies"
    assert ProfileTechnology.__tablename__ == "profile_technologies"
