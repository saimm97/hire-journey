"""Tests for the computed onboarding-completion rule."""

import pytest

from app.models.profile import Profile
from app.services.profile_service import is_onboarding_complete, onboarding_completion_issues


def _profile(**overrides) -> Profile:
    fields = dict(
        source_resume_id=1,
        first_name="Jane",
        last_name="Smith",
        title="Engineer",
        desired_roles=["backend"],
        desired_locations=["Berlin"],
        work_modes_preferred=["remote"],
        seniority_level="senior",
    )
    fields.update(overrides)
    return Profile(**fields)


def test_complete_profile():
    assert is_onboarding_complete(_profile())
    assert onboarding_completion_issues(_profile()) == []


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
        {"desired_locations": []},
        {"work_modes_preferred": []},
        {"seniority_level": None},
        {"seniority_level": "  "},
    ],
)
def test_each_missing_core_field_is_incomplete(overrides):
    assert not is_onboarding_complete(_profile(**overrides))


def test_completion_issues_name_every_missing_field_and_step():
    profile = _profile(
        first_name=" ",
        last_name=None,
        title="",
        desired_roles=[],
        desired_locations=[],
        work_modes_preferred=[],
        seniority_level=None,
    )

    issues = onboarding_completion_issues(profile)

    assert [(issue.step, issue.path) for issue in issues] == [
        ("profile", ["first_name"]),
        ("profile", ["last_name"]),
        ("profile", ["title"]),
        ("preferences", ["desired_roles"]),
        ("preferences", ["desired_locations"]),
        ("preferences", ["work_modes_preferred"]),
        ("preferences", ["seniority_level"]),
    ]
