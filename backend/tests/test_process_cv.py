"""Postgres-backed tests for resume-upload persistence (process_cv).

The LLM call is stubbed; everything downstream (transaction, company
resolution, employment/project/technology replacement) runs against the
real database.
"""

import asyncio
import uuid
from datetime import date

import fitz
import pytest
from sqlalchemy import delete, func, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Company, EmploymentHistory, Profile, Resume, User
from app.schemas.extraction import (
    EducationItem,
    EmploymentItem,
    ProjectItem,
    ResumeExtraction,
)
from app.services import profile_service, resume_service


def _pdf_bytes(text: str = "Resume") -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _stub_extraction(monkeypatch, extraction: ResumeExtraction) -> None:
    async def fake_extract(system, user, schema, **kwargs):
        return extraction

    monkeypatch.setattr(profile_service.llm, "structured_extract", fake_extract)


async def _cleanup_companies(db, profile_id: int | None, *names: str) -> None:
    """Remove test companies; employment rows must go first (RESTRICT FK)."""
    if profile_id is not None:
        await db.execute(
            delete(EmploymentHistory).where(EmploymentHistory.profile_id == profile_id)
        )
    await db.execute(delete(Company).where(Company.name.in_(names)))
    await db.commit()


async def test_upload_populates_all_tables(db, test_user, monkeypatch):
    marker = uuid.uuid4().hex[:8]
    acme = f"Acme {marker}"
    _stub_extraction(
        monkeypatch,
        ResumeExtraction(
            first_name="Jane",
            last_name="Smith",
            phone_number=" +49 123 ",
            location="Berlin, Germany",
            title="Backend Engineer",
            summary="Builds APIs.",
            github_url="github.com/jane",
            linkedin_url="https://linkedin.com/in/jane",
            portfolio_url="not a url",
            technologies=["Python", " python ", "FastAPI"],
            education=[
                EducationItem(institution="TU Berlin", degree="BSc"),
                EducationItem(degree="dropped — no institution"),
            ],
            employment_history=[
                EmploymentItem(
                    company_name=f"  {acme}  ",
                    title="Engineer",
                    start_date="2021-05",
                    end_date="Present",
                    description="Built things.",
                ),
                EmploymentItem(company_name=acme, title=None),  # dropped: no title
                EmploymentItem(
                    company_name=acme, title="Intern", start_date="2023-01", end_date="2022-01"
                ),  # contradictory dates -> both nulled
            ],
            projects=[
                ProjectItem(name="Career Engine", technologies=["LangChain"]),
                ProjectItem(summary="dropped — no name"),
            ],
        ),
    )

    profile, projects, summary = await profile_service.process_cv(
        db, test_user.id, "cv.pdf", _pdf_bytes()
    )

    try:
        assert profile.first_name == "Jane"
        assert profile.phone_number == "+49 123"
        assert profile.location == "Berlin, Germany"
        assert profile.title == "Backend Engineer"
        # URL normalization: bare domain prefixed, malformed dropped
        assert profile.social_links == {
            "github_url": "https://github.com/jane",
            "linkedin_url": "https://linkedin.com/in/jane",
        }
        # JSONB entries missing their required field are dropped
        assert len(profile.education) == 1
        assert profile.education[0]["institution"] == "TU Berlin"
        # profile_technologies is the overall skill set: the top-level list
        # unioned with every project's tech (langchain), lowercased and deduped
        assert sorted(link.name for link in profile.technologies) == [
            "fastapi",
            "langchain",
            "python",
        ]
        # source resume linked and raw extraction preserved (incl. dropped entries)
        resume = (
            await db.execute(select(Resume).where(Resume.id == profile.source_resume_id))
        ).scalar_one()
        assert len(resume.parsed_content["employment_history"]) == 3
        assert len(resume.parsed_content["education"]) == 2

        employments = (
            (
                await db.execute(
                    select(EmploymentHistory).where(EmploymentHistory.profile_id == profile.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(employments) == 2  # the title-less entry was dropped
        by_title = {e.title: e for e in employments}
        assert by_title["Engineer"].start_date == date(2021, 5, 1)
        assert by_title["Engineer"].end_date is None  # "Present"
        assert by_title["Intern"].start_date is None  # contradictory pair nulled
        assert by_title["Intern"].end_date is None
        # both entries resolved to ONE company row, whitespace-normalized
        assert len({e.company_id for e in employments}) == 1
        company = (
            await db.execute(select(Company).where(Company.id == employments[0].company_id))
        ).scalar_one()
        assert company.name == acme
        assert company.slug is None  # resume employers are never scan targets

        assert [p.name for p in projects] == ["Career Engine"]
        assert projects[0].tech_stack == ["langchain"]
        assert summary == "Builds APIs."
    finally:
        await _cleanup_companies(db, profile.id, acme)


async def test_company_reused_case_insensitively_and_never_deleted(db, test_user, monkeypatch):
    marker = uuid.uuid4().hex[:8]
    zeta = f"Zeta {marker}"
    yco = f"Yco {marker}"
    db.add(Company(name=zeta, slug=f"zeta-{marker}"))
    await db.commit()

    _stub_extraction(
        monkeypatch,
        ResumeExtraction(
            first_name="A",
            employment_history=[EmploymentItem(company_name=zeta.lower(), title="Dev")],
        ),
    )
    profile, _, _ = await profile_service.process_cv(db, test_user.id, "cv.pdf", _pdf_bytes())

    try:
        rows = (
            (await db.execute(select(Company).where(func.lower(Company.name) == zeta.lower())))
            .scalars()
            .all()
        )
        assert len(rows) == 1  # reused, not duplicated
        assert rows[0].slug == f"zeta-{marker}"  # ATS slug untouched

        # Re-upload with a different employer: employment rows replaced,
        # but the old company row must survive.
        _stub_extraction(
            monkeypatch,
            ResumeExtraction(
                first_name="A",
                employment_history=[EmploymentItem(company_name=yco, title="Dev")],
            ),
        )
        await profile_service.process_cv(
            db, test_user.id, "cv2.pdf", _pdf_bytes(), replace_resume_id=profile.source_resume_id
        )
        zeta_still = (
            await db.execute(select(Company).where(Company.name == zeta))
        ).scalar_one_or_none()
        assert zeta_still is not None
    finally:
        await _cleanup_companies(db, profile.id, zeta, yco)


async def test_reupload_replaces_and_clears_but_keeps_preferences(db, test_user, monkeypatch):
    _stub_extraction(
        monkeypatch,
        ResumeExtraction(first_name="Jane", phone_number="123", technologies=["Python"]),
    )
    await profile_service.process_cv(db, test_user.id, "cv.pdf", _pdf_bytes())
    await profile_service.update_profile(db, test_user.id, {"desired_roles": ["backend"]})

    profile_before = (
        await db.execute(select(Profile).where(Profile.user_id == test_user.id))
    ).scalar_one()
    source_id = profile_before.source_resume_id

    # New resume: phone and technologies absent -> cleared, preferences kept
    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Janet"))
    profile, _, _ = await profile_service.process_cv(
        db, test_user.id, "cv2.pdf", _pdf_bytes(), replace_resume_id=source_id
    )

    assert profile.first_name == "Janet"
    assert profile.phone_number is None  # cleared
    assert profile.technologies == []  # cleared
    assert profile.desired_roles == ["backend"]  # preferences untouched
    count = await db.scalar(
        select(func.count()).select_from(Resume).where(Resume.user_id == test_user.id)
    )
    assert count == 1  # replaced in place, no second slot consumed


async def test_failure_rolls_back_everything(db, test_user, monkeypatch):
    # Capture the plain int: the rollback below expires ORM attributes.
    user_id = test_user.id
    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Jane"))

    async def boom(db_, profile_id, projects):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(profile_service, "replace_projects", boom)

    with pytest.raises(RuntimeError):
        await profile_service.process_cv(db, user_id, "cv.pdf", _pdf_bytes())

    assert (
        await db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user_id))
    ) == 0
    assert (
        await db.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none() is None


async def test_cannot_replace_another_users_resume(db, test_user, monkeypatch):
    other = User(
        username=f"pytest-{uuid.uuid4().hex[:12]}",
        email=f"pytest-{uuid.uuid4().hex[:12]}@example.test",
    )
    db.add(other)
    await db.commit()
    await db.refresh(other)
    other_resume = Resume(user_id=other.id, file_name="other.pdf")
    db.add(other_resume)
    await db.commit()
    await db.refresh(other_resume)
    # Plain ints: the rollback below expires ORM attributes.
    user_id, other_id, other_resume_id = test_user.id, other.id, other_resume.id

    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Jane"))
    try:
        with pytest.raises(resume_service.ResumeNotFoundError):
            await profile_service.process_cv(
                db, user_id, "cv.pdf", _pdf_bytes(), replace_resume_id=other_resume_id
            )
    finally:
        await db.execute(delete(User).where(User.id == other_id))
        await db.commit()


async def test_resume_limit_enforced(db, test_user, monkeypatch):
    user_id = test_user.id
    for n in range(2):
        db.add(Resume(user_id=user_id, file_name=f"r{n}.pdf"))
    await db.commit()

    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Jane"))
    with pytest.raises(resume_service.ResumeLimitError):
        await profile_service.process_cv(db, user_id, "cv.pdf", _pdf_bytes())


async def test_identical_upload_reuses_resume(db, test_user, monkeypatch):
    user_id = test_user.id
    data = _pdf_bytes("Same content")
    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Jane"))

    first_profile, _, _ = await profile_service.process_cv(db, user_id, "first.pdf", data)
    first_resume_id = first_profile.source_resume_id
    second_profile, _, _ = await profile_service.process_cv(db, user_id, "retry.pdf", data)

    assert second_profile.source_resume_id == first_resume_id
    assert (
        await db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user_id))
    ) == 1
    resume = await db.get(Resume, first_resume_id)
    assert resume is not None
    assert resume.file_name == "retry.pdf"
    assert resume.parsed_content["first_name"] == "Jane"


async def test_different_uploads_create_separate_resumes(db, test_user, monkeypatch):
    user_id = test_user.id
    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Jane"))

    first_profile, _, _ = await profile_service.process_cv(
        db, user_id, "first.pdf", _pdf_bytes("First resume")
    )
    first_resume_id = first_profile.source_resume_id
    second_profile, _, _ = await profile_service.process_cv(
        db, user_id, "second.pdf", _pdf_bytes("Second resume")
    )

    assert second_profile.source_resume_id != first_resume_id
    assert (
        await db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user_id))
    ) == 2


async def test_identical_upload_reuses_resume_at_limit(db, test_user, monkeypatch):
    user_id = test_user.id
    data = _pdf_bytes("Already stored")
    raw_content = profile_service.document_parser.to_text(data, "stored.pdf")
    matching = Resume(user_id=user_id, file_name="stored.pdf", raw_content=raw_content)
    other = Resume(user_id=user_id, file_name="other.pdf", raw_content="different")
    db.add_all([matching, other])
    await db.commit()
    await db.refresh(matching)
    matching_id = matching.id
    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Jane"))

    profile, _, _ = await profile_service.process_cv(db, user_id, "retry.pdf", data)

    assert profile.source_resume_id == matching_id
    assert (
        await db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user_id))
    ) == settings.max_resumes_per_user


async def test_concurrent_identical_uploads_create_one_resume(db, test_user, monkeypatch):
    user_id = test_user.id
    data = _pdf_bytes("Concurrent retry")
    _stub_extraction(monkeypatch, ResumeExtraction(first_name="Jane"))

    async def upload() -> None:
        async with AsyncSessionLocal() as session:
            await profile_service.process_cv(session, user_id, "cv.pdf", data)

    await asyncio.gather(upload(), upload())

    assert (
        await db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user_id))
    ) == 1


async def test_concurrent_company_resolution_creates_one_row(db):
    name = f"Rocket {uuid.uuid4().hex[:8]}"

    async def resolve() -> None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await profile_service._get_or_create_company(session, name)

    await asyncio.gather(resolve(), resolve())

    try:
        count = await db.scalar(
            select(func.count()).select_from(Company).where(Company.name == name)
        )
        assert count == 1  # advisory lock serialized the duplicate insert
    finally:
        await _cleanup_companies(db, None, name)
