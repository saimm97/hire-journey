"""Tests for the computed onboarding-completion rule."""

import pytest

from app.models.profile import Profile
from app.services.profile_service import is_onboarding_complete


def _profile(**overrides) -> Profile:
    fields = dict(
        source_resume_id=1,
        first_name="Jane",
        last_name="Smith",
        title="Engineer",
        desired_roles=["backend"],
        work_modes_preferred=["remote"],
        seniority_level="senior",
    )
    fields.update(overrides)
    return Profile(**fields)


def test_complete_profile():
    assert is_onboarding_complete(_profile())


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_resume_id": None},
        {"first_name": None},
        {"first_name": "   "},
        {"last_name": None},
        {"title": None},
        {"title": ""},
        {"desired_roles": []},
        {"work_modes_preferred": []},
        {"seniority_level": None},
        {"seniority_level": "  "},
    ],
)
def test_each_missing_core_field_is_incomplete(overrides):
    assert not is_onboarding_complete(_profile(**overrides))
