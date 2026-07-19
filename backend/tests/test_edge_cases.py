"""Adversarial edge-case tests for the onboarding pipeline.

Covers hostile-but-plausible inputs: unbounded LLM output vs column limits,
duplicate extraction entries, empty extractions, oversized payloads, and
upload-size enforcement.
"""

import uuid

from sqlalchemy import delete, func, select

from app.config import settings
from app.models import Company, EmploymentHistory, Profile, ProfileProject
from app.schemas.extraction import EmploymentItem, ProjectItem, ResumeExtraction
from app.services import profile_service
from tests.test_process_cv import _pdf_bytes, _stub_extraction


async def _cleanup_companies(db, profile_id, *names):
    if profile_id is not None:
        await db.execute(
            delete(EmploymentHistory).where(EmploymentHistory.profile_id == profile_id)
        )
    await db.execute(delete(Company).where(Company.name.in_(names)))
    await db.commit()


async def test_duplicate_extraction_entries_collapse(db, test_user, monkeypatch):
    """The LLM can surface the same project/stint from two resume sections."""
    marker = uuid.uuid4().hex[:8]
    acme = f"EdgeCo {marker}"
    _stub_extraction(
        monkeypatch,
        ResumeExtraction(
            first_name="Jane",
            projects=[
                ProjectItem(name="Zenn - Focus App"),
                ProjectItem(name="  zenn - focus  app "),  # same, different case/spacing
                ProjectItem(name="Other"),
            ],
            employment_history=[
                EmploymentItem(company_name=acme, title="Dev", start_date="2021-05"),
                EmploymentItem(company_name=acme.upper(), title="dev", start_date="2021-05"),
            ],
        ),
    )
    profile, projects, _ = await profile_service.process_cv(
        db, test_user.id, "cv.pdf", _pdf_bytes()
    )
    try:
        assert sorted(p.name for p in projects) == ["Other", "Zenn - Focus App"]
        employments = (
            await db.scalars(
                select(EmploymentHistory).where(EmploymentHistory.profile_id == profile.id)
            )
        ).all()
        assert len(employments) == 1  # duplicate stint collapsed
    finally:
        await _cleanup_companies(db, profile.id, acme)


async def test_oversized_llm_values_are_clipped_not_500(db, test_user, monkeypatch):
    """Unbounded LLM strings must not blow up on String(N) columns."""
    marker = uuid.uuid4().hex[:8]
    long_company = f"L{marker} " + "x" * 300
    _stub_extraction(
        monkeypatch,
        ResumeExtraction(
            first_name="J" * 300,
            phone_number="1" * 90,
            title="🚀 " + "t" * 300,  # unicode + oversize together
            technologies=["k" * 150],
            employment_history=[EmploymentItem(company_name=long_company, title="T" * 300)],
            projects=[
                ProjectItem(name="P" * 300, github_url="https://example.com/" + "a" * 300)
            ],
        ),
    )
    profile, projects, _ = await profile_service.process_cv(
        db, test_user.id, "cv.pdf", _pdf_bytes()
    )
    try:
        assert len(profile.first_name) == 100
        assert len(profile.phone_number) == 50
        assert len(profile.title) == 255
        assert all(len(link.name) <= 100 for link in profile.technologies)
        assert len(projects[0].name) == 255
        assert projects[0].github_url is None  # over-limit URL dropped, not truncated
        company_name = await db.scalar(
            select(Company.name).where(Company.name.like(f"L{marker}%"))
        )
        assert len(company_name) == 255
    finally:
        await _cleanup_companies(db, profile.id, (f"L{marker} " + "x" * 300)[:255])


async def test_completely_empty_extraction_still_onboards(db, test_user, monkeypatch):
    """A resume the LLM can't extract anything from must still create state."""
    _stub_extraction(monkeypatch, ResumeExtraction())
    profile, projects, summary = await profile_service.process_cv(
        db, test_user.id, "cv.pdf", _pdf_bytes()
    )
    assert profile.source_resume_id is not None
    assert profile.first_name is None
    assert projects == []
    assert summary is None
    memberships = await db.scalar(
        select(func.count())
        .select_from(ProfileProject)
        .where(ProfileProject.profile_id == profile.id)
    )
    assert memberships == 0


async def test_salary_overflow_rejected(client, db, test_user):
    await db.execute(
        select(Profile.id)  # ensure session usable; profile seeded below
    )
    from tests.test_onboarding_api import _seed_profile

    await _seed_profile(db, test_user.id)
    payload = {
        "minimum_salary": 3_000_000_000,  # would overflow the int32 column
        "desired_roles": ["backend"],
        "work_modes_preferred": ["remote"],
        "seniority_level": "senior",
    }
    assert (await client.put("/api/v1/profile/preferences", json=payload)).status_code == 422


async def test_oversized_collections_rejected(client, db, test_user):
    from tests.test_onboarding_api import _seed_profile

    await _seed_profile(db, test_user.id)
    too_many_roles = {
        "desired_roles": [f"role-{i}" for i in range(101)],
        "work_modes_preferred": ["remote"],
        "seniority_level": "senior",
    }
    assert (
        await client.put("/api/v1/profile/preferences", json=too_many_roles)
    ).status_code == 422

    ancient_month = {
        "employment_history": [
            {"company_name": "X", "title": "Y", "start_date": "1850-01"}
        ]
    }
    assert (await client.put("/api/v1/profile/details", json=ancient_month)).status_code == 422

    huge_url = {"social_links": {"github_url": "https://example.com/" + "a" * 300}}
    assert (await client.put("/api/v1/profile/details", json=huge_url)).status_code == 422


async def test_upload_size_enforced_after_read(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    response = await client.post(
        "/api/v1/profile/cv",
        files={"file": ("cv.pdf", _pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 413
