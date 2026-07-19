"""API tests for the onboarding snapshot, details, and preferences steps."""

import uuid

from sqlalchemy import delete, func, select

from app.models import Company, EmploymentHistory, Profile, ProfileProject, Project, Resume, User
from app.schemas.profile import ProjectEntry
from app.services import profile_service


async def _seed_profile(db, user_id: int, *, with_resume: bool = True, **fields) -> int:
    """Create a profile row (and optionally its source resume) directly."""
    if with_resume:
        resume = Resume(user_id=user_id, file_name="cv.pdf", parsed_content={"summary": "S."})
        db.add(resume)
        await db.flush()
        fields.setdefault("source_resume_id", resume.id)
    await profile_service.upsert_profile(db, user_id, fields)
    await db.commit()
    return await db.scalar(select(Profile.id).where(Profile.user_id == user_id))


# ── Snapshot ───────────────────────────────────────────────────────────


async def test_snapshot_404_without_profile(client):
    assert (await client.get("/api/v1/profile")).status_code == 404


async def test_snapshot_shape(client, db, test_user):
    await _seed_profile(db, test_user.id, first_name="Jane")
    body = (await client.get("/api/v1/profile")).json()

    assert body["profile"]["first_name"] == "Jane"
    assert body["profile"]["account_email"] == test_user.email
    # metadata only — never the raw resume text
    assert set(body["source_resume"]) == {"id", "file_name", "created_at", "summary"}
    assert body["source_resume"]["file_name"] == "cv.pdf"
    assert body["source_resume"]["summary"] == "S."
    assert body["employment_history"] == []
    assert body["projects"] == []
    assert body["onboarding_complete"] is False


# ── Details step ───────────────────────────────────────────────────────


async def test_details_roundtrip(client, db, test_user):
    marker = uuid.uuid4().hex[:8]
    user_id = test_user.id
    await _seed_profile(db, user_id)
    payload = {
        "first_name": "Jane",
        "last_name": "Smith",
        "phone_number": "+49 123",
        "location": "Berlin",
        "title": "Backend Engineer",
        "summary": "Builds APIs.",
        "social_links": {"github_url": "github.com/jane"},
        "education": [
            {
                "institution": "TU Berlin",
                "degree": "BSc",
                "start_date": "2016-10",
                "end_date": "2019-09",
            }
        ],
        "certifications": [{"name": "AWS SAA", "issued_at": "2023-03"}],
        "employment_history": [
            {
                "company_name": f"DetCo {marker}",
                "title": "Dev",
                "start_date": "2021-05",
                "end_date": "2023-01",
            }
        ],
        "projects": [{"name": "Career Engine", "technologies": ["Python", "python"]}],
        "technologies": ["Python", " python ", "FastAPI"],
    }

    response = await client.put("/api/v1/profile/details", json=payload)

    try:
        assert response.status_code == 200
        body = response.json()
        profile = body["profile"]
        assert profile["first_name"] == "Jane"
        assert profile["title"] == "Backend Engineer"
        assert profile["social_links"] == {"github_url": "https://github.com/jane"}
        assert profile["education"][0]["institution"] == "TU Berlin"
        assert profile["certifications"][0]["name"] == "AWS SAA"
        assert sorted(profile["technologies"]) == ["fastapi", "python"]
        assert body["employment_history"][0]["company_name"] == f"DetCo {marker}"
        assert body["employment_history"][0]["start_date"] == "2021-05-01"
        assert [p["name"] for p in body["projects"]] == ["Career Engine"]
        assert body["projects"][0]["tech_stack"] == ["python"]
        assert body["onboarding_complete"] is False  # preferences still unset
    finally:
        profile_id = await db.scalar(select(Profile.id).where(Profile.user_id == user_id))
        await db.execute(
            delete(EmploymentHistory).where(EmploymentHistory.profile_id == profile_id)
        )
        await db.execute(delete(Company).where(Company.name == f"DetCo {marker}"))
        await db.commit()


async def test_details_validation_errors(client, db, test_user):
    await _seed_profile(db, test_user.id)
    bad_payloads = [
        # month must be YYYY-MM
        {"employment_history": [{"company_name": "X", "title": "Y", "start_date": "2021-13"}]},
        {"employment_history": [{"company_name": "X", "title": "Y", "start_date": "May 2021"}]},
        # end before start
        {
            "employment_history": [
                {
                    "company_name": "X",
                    "title": "Y",
                    "start_date": "2022-01",
                    "end_date": "2021-01",
                }
            ]
        },
        # employment requires company and title
        {"employment_history": [{"company_name": "X", "title": ""}]},
        # education requires an institution
        {"education": [{"institution": ""}]},
        # social links must be URLs
        {"social_links": {"github_url": "not a url"}},
    ]
    for payload in bad_payloads:
        assert (await client.put("/api/v1/profile/details", json=payload)).status_code == 422


async def test_details_rejects_foreign_project_id(client, db, test_user):
    await _seed_profile(db, test_user.id)
    response = await client.put(
        "/api/v1/profile/details",
        json={"projects": [{"project_id": 99999999, "name": "X"}]},
    )
    assert response.status_code == 422


async def test_details_requires_profile(client):
    assert (await client.put("/api/v1/profile/details", json={})).status_code == 404


# ── Project reconciliation (service level) ─────────────────────────────


async def test_unshared_project_rename_updates_in_place_and_omission_deletes(db, test_user):
    profile_id = await _seed_profile(db, test_user.id, with_resume=False)
    await profile_service.save_projects(db, profile_id, [ProjectEntry(name="P1")])
    await db.commit()
    [project] = await profile_service._load_projects(db, profile_id)

    await profile_service.save_projects(
        db, profile_id, [ProjectEntry(project_id=project.project_id, name="P1 renamed")]
    )
    await db.commit()
    [renamed] = await profile_service._load_projects(db, profile_id)
    assert renamed.project_id == project.project_id  # same identity
    assert renamed.name == "P1 renamed"

    await profile_service.save_projects(db, profile_id, [])
    await db.commit()
    assert await profile_service._load_projects(db, profile_id) == []
    orphaned = await db.scalar(
        select(func.count()).select_from(Project).where(Project.id == project.project_id)
    )
    assert orphaned == 0  # unreferenced project is orphan-deleted


async def test_shared_project_rename_copies_on_write(db, test_user):
    other = User(
        username=f"pytest-{uuid.uuid4().hex[:12]}",
        email=f"pytest-{uuid.uuid4().hex[:12]}@example.test",
    )
    db.add(other)
    await db.commit()
    await db.refresh(other)
    other_id = other.id

    profile_id = await _seed_profile(db, test_user.id, with_resume=False)
    other_profile_id = await _seed_profile(db, other_id, with_resume=False)
    project = Project(name="Shared")
    db.add(project)
    await db.flush()
    db.add(ProfileProject(profile_id=profile_id, project_id=project.id))
    db.add(ProfileProject(profile_id=other_profile_id, project_id=project.id))
    await db.commit()
    project_id = project.id

    try:
        await profile_service.save_projects(
            db, profile_id, [ProjectEntry(project_id=project_id, name="Renamed")]
        )
        await db.commit()

        # this profile got a NEW project identity with the new name
        [mine] = await profile_service._load_projects(db, profile_id)
        assert mine.name == "Renamed"
        assert mine.project_id != project_id
        # the other profile's project is untouched
        [theirs] = await profile_service._load_projects(db, other_profile_id)
        assert theirs.project_id == project_id
        assert theirs.name == "Shared"
    finally:
        await db.execute(delete(User).where(User.id == other_id))
        await db.commit()


# ── Preferences step ───────────────────────────────────────────────────


async def test_preferences_happy_path_completes_onboarding(client, db, test_user):
    await _seed_profile(db, test_user.id, first_name="Jane", last_name="S", title="Eng")
    payload = {
        "minimum_salary": 60000,
        "desired_roles": ["Backend ", "backend", ""],
        "desired_locations": ["Berlin"],
        "work_modes_preferred": ["remote", "remote", "hybrid"],
        "seniority_level": "senior",
    }

    response = await client.put("/api/v1/profile/preferences", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["minimum_salary"] == 60000
    assert body["profile"]["desired_roles"] == ["Backend"]  # trimmed + deduped
    assert body["profile"]["work_modes_preferred"] == ["remote", "hybrid"]  # deduped
    assert body["profile"]["seniority_level"] == "senior"
    assert body["onboarding_complete"] is True


async def test_preferences_validation_errors(client, db, test_user):
    await _seed_profile(db, test_user.id)
    valid = {
        "desired_roles": ["backend"],
        "work_modes_preferred": ["remote"],
        "seniority_level": "senior",
    }
    bad_payloads = [
        {**valid, "desired_roles": []},
        {**valid, "desired_roles": ["   "]},  # cleans to empty
        {**valid, "work_modes_preferred": []},
        {**valid, "work_modes_preferred": ["office"]},  # not a valid mode
        {**valid, "seniority_level": "boss"},  # not a valid level
        {**valid, "minimum_salary": -1},
    ]
    for payload in bad_payloads:
        assert (
            await client.put("/api/v1/profile/preferences", json=payload)
        ).status_code == 422


async def test_preferences_requires_profile(client):
    payload = {
        "desired_roles": ["backend"],
        "work_modes_preferred": ["remote"],
        "seniority_level": "senior",
    }
    assert (await client.put("/api/v1/profile/preferences", json=payload)).status_code == 404
