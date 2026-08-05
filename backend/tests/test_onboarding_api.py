"""API tests for the onboarding snapshot and the unified PATCH /profile update.

Both correction screens (details, preferences) persist through one endpoint.
An omitted section is left untouched; a supplied section is fully replaced.
"""

import uuid

from sqlalchemy import delete, func, select

from app import messages
from app.models import Company, EmploymentHistory, Profile, ProfileProject, Project, Resume, User
from app.schemas.profile import ProjectEntry
from app.services import profile_service
from app.services.profile import projects


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
    assert [issue["path"] for issue in body["completion_issues"]] == [
        ["last_name"],
        ["title"],
        ["desired_roles"],
        ["desired_locations"],
        ["work_modes_preferred"],
        ["seniority_level"],
    ]


_PREFS = {
    "desired_roles": ["Backend Engineer"],
    "desired_locations": ["Berlin"],
    "work_modes_preferred": ["remote"],
    "seniority_level": "senior",
}


# ── Update: details section ────────────────────────────────────────────


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
                "start_date": "2016",
                "end_date": "2019-09",
            },
            {"institution": "Self-directed study"},
        ],
        "certifications": [{"name": "AWS SAA", "issued_at": "2023"}],
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

    response = await client.patch("/api/v1/profile", json={"details": payload})

    try:
        assert response.status_code == 200
        body = response.json()
        profile = body["profile"]
        assert profile["first_name"] == "Jane"
        assert profile["title"] == "Backend Engineer"
        assert profile["social_links"] == {"github_url": "https://github.com/jane"}
        assert profile["education"][0]["institution"] == "TU Berlin"
        assert profile["education"][0]["start_date"] == "2016"
        assert profile["education"][1]["start_date"] is None
        assert profile["certifications"][0]["name"] == "AWS SAA"
        assert profile["certifications"][0]["issued_at"] == "2023"
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
        response = await client.patch("/api/v1/profile", json={"details": payload})
        assert response.status_code == 422


async def test_details_validation_error_returns_actionable_field_path(client, db, test_user):
    await _seed_profile(db, test_user.id)

    response = await client.patch(
        "/api/v1/profile",
        json={
            "details": {
                "education": [
                    {
                        "institution": "TU Berlin",
                        "start_date": "May 2021",
                    }
                ]
            }
        },
    )

    assert response.status_code == 422
    # The path is section-qualified now; the client strips the leading section
    # segment so form controls keep matching on the bare field path.
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Some details need fixing.",
            "fields": [
                {
                    "path": ["details", "education", 0, "start_date"],
                    "message": "must be in YYYY or YYYY-MM format",
                }
            ],
        }
    }


async def test_details_rejects_reversed_dates_on_the_end_fields(client, db, test_user):
    await _seed_profile(db, test_user.id)

    response = await client.patch(
        "/api/v1/profile",
        json={
            "details": {
                "education": [
                    {
                        "institution": "TU Berlin",
                        "start_date": "2026",
                        "end_date": "2012",
                    }
                ],
                "certifications": [
                    {
                        "name": "AWS",
                        "issued_at": "2025-09",
                        "expires_at": "2025-03",
                    }
                ],
            }
        },
    )

    assert response.status_code == 422
    fields = {
        tuple(field["path"]): field["message"] for field in response.json()["error"]["fields"]
    }
    assert fields == {
        (
            "details",
            "education",
            0,
            "end_date",
        ): "education end date cannot precede its start date",
        (
            "details",
            "certifications",
            0,
            "expires_at",
        ): "expiration date cannot precede its issue date",
    }


async def test_details_accepts_same_year_when_only_one_date_has_month_precision(
    client, db, test_user
):
    await _seed_profile(db, test_user.id)

    response = await client.patch(
        "/api/v1/profile",
        json={
            "details": {
                "education": [
                    {
                        "institution": "TU Berlin",
                        "start_date": "2021-09",
                        "end_date": "2021",
                    }
                ]
            }
        },
    )

    assert response.status_code == 200


async def test_details_rejects_foreign_project_id(client, db, test_user):
    await _seed_profile(db, test_user.id)
    response = await client.patch(
        "/api/v1/profile",
        json={
            "details": {
                "projects": [
                    {"name": "New project"},
                    {"project_id": 99999999, "name": "Stale project"},
                ]
            }
        },
    )
    # A stale/foreign project_id is a conflict to resolve by reloading, not bad input.
    assert response.status_code == 409
    # Hand-built by the ownership handler, so it carries no section segment —
    # which is already the post-strip shape the editor rows are keyed on.
    assert response.json() == {
        "error": {
            "code": "projects_stale",
            "message": messages.PROJECTS_STALE,
            "fields": [
                {
                    "path": ["projects", 1],
                    "message": messages.PROJECTS_STALE,
                }
            ],
        }
    }


async def test_details_requires_profile(client):
    response = await client.patch("/api/v1/profile", json={"details": {}})
    assert response.status_code == 404


# ── Project reconciliation (service level) ─────────────────────────────


async def test_unshared_project_rename_updates_in_place_and_omission_deletes(db, test_user):
    profile_id = await _seed_profile(db, test_user.id, with_resume=False)
    await projects.save_projects(db, profile_id, [ProjectEntry(name="P1")])
    await db.commit()
    [project] = await projects.load_projects(db, profile_id)

    await projects.save_projects(
        db, profile_id, [ProjectEntry(project_id=project.project_id, name="P1 renamed")]
    )
    await db.commit()
    [renamed] = await projects.load_projects(db, profile_id)
    assert renamed.project_id == project.project_id  # same identity
    assert renamed.name == "P1 renamed"

    await projects.save_projects(db, profile_id, [])
    await db.commit()
    assert await projects.load_projects(db, profile_id) == []
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
        await projects.save_projects(
            db, profile_id, [ProjectEntry(project_id=project_id, name="Renamed")]
        )
        await db.commit()

        # this profile got a NEW project identity with the new name
        [mine] = await projects.load_projects(db, profile_id)
        assert mine.name == "Renamed"
        assert mine.project_id != project_id
        # the other profile's project is untouched
        [theirs] = await projects.load_projects(db, other_profile_id)
        assert theirs.project_id == project_id
        assert theirs.name == "Shared"
    finally:
        await db.execute(delete(User).where(User.id == other_id))
        await db.commit()


# ── Update: preferences section ────────────────────────────────────────


async def test_preferences_happy_path_completes_onboarding(client, db, test_user):
    await _seed_profile(db, test_user.id, first_name="Jane", last_name="S", title="Eng")
    payload = {
        "minimum_salary": 60000,
        "desired_roles": ["Backend ", "backend", ""],
        "desired_locations": ["Berlin"],
        "work_modes_preferred": ["remote", "remote", "hybrid"],
        "seniority_level": "senior",
    }

    response = await client.patch("/api/v1/profile", json={"preferences": payload})

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["minimum_salary"] == 60000
    assert body["profile"]["desired_roles"] == ["Backend"]  # trimmed + deduped
    assert body["profile"]["work_modes_preferred"] == ["remote", "hybrid"]  # deduped
    assert body["profile"]["seniority_level"] == "senior"
    assert body["onboarding_complete"] is True
    assert body["completion_issues"] == []


async def test_preferences_validation_errors(client, db, test_user):
    await _seed_profile(db, test_user.id)
    valid = {
        "desired_roles": ["backend"],
        "desired_locations": ["Berlin"],
        "work_modes_preferred": ["remote"],
        "seniority_level": "senior",
    }
    bad_payloads = [
        {**valid, "desired_roles": []},
        {**valid, "desired_roles": ["   "]},  # cleans to empty
        {**valid, "desired_locations": []},
        {**valid, "desired_locations": ["   "]},  # cleans to empty
        {**valid, "work_modes_preferred": []},
        {**valid, "work_modes_preferred": ["office"]},  # not a valid mode
        {**valid, "seniority_level": "boss"},  # not a valid level
        {**valid, "minimum_salary": -1},
    ]
    for payload in bad_payloads:
        response = await client.patch("/api/v1/profile", json={"preferences": payload})
        assert response.status_code == 422


async def test_preferences_requires_profile(client):
    payload = {
        "desired_roles": ["backend"],
        "desired_locations": ["Berlin"],
        "work_modes_preferred": ["remote"],
        "seniority_level": "senior",
    }
    response = await client.patch("/api/v1/profile", json={"preferences": payload})
    assert response.status_code == 404


async def test_preferences_empty_lists_are_field_addressable(client, db, test_user):
    # The required-list rejections must carry a concrete path (field_validator,
    # not model_validator) so the UI can highlight the exact control.
    await _seed_profile(db, test_user.id)
    response = await client.patch(
        "/api/v1/profile",
        json={
            "preferences": {
                "desired_roles": [],
                "desired_locations": [],
                "work_modes_preferred": [],
                "seniority_level": "senior",
            }
        },
    )
    assert response.status_code == 422
    paths = {tuple(field["path"]) for field in response.json()["error"]["fields"]}
    assert ("preferences", "desired_roles") in paths
    assert ("preferences", "desired_locations") in paths
    assert ("preferences", "work_modes_preferred") in paths


# ── Update: section semantics ──────────────────────────────────────────


async def test_update_requires_at_least_one_section(client, db, test_user):
    await _seed_profile(db, test_user.id, first_name="Jane")
    assert (await client.patch("/api/v1/profile", json={})).status_code == 422


async def test_update_rejects_unknown_keys(client, db, test_user):
    """A typo must 422, never silently clear the rest of a replaced section."""
    await _seed_profile(db, test_user.id, first_name="Jane", title="Eng")

    # Misspelled section: the sibling section would otherwise commit alone.
    misspelled_section = {"details": {"first_name": "Ada"}, "prefrences": _PREFS}
    assert (await client.patch("/api/v1/profile", json=misspelled_section)).status_code == 422

    # Misspelled field: every other details column defaults, so accepting this
    # would wipe first_name, title, education, projects and technologies.
    misspelled_field = {"details": {"frist_name": "Ada"}}
    assert (await client.patch("/api/v1/profile", json=misspelled_field)).status_code == 422

    # Nothing was written.
    profile = (await client.get("/api/v1/profile")).json()["profile"]
    assert profile["first_name"] == "Jane"
    assert profile["title"] == "Eng"


async def test_details_only_leaves_preferences_intact(client, db, test_user):
    await _seed_profile(db, test_user.id, first_name="Old", **_PREFS)

    response = await client.patch(
        "/api/v1/profile",
        json={"details": {"first_name": "Jane", "last_name": "Doe", "title": "Eng"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["first_name"] == "Jane"
    assert body["profile"]["desired_roles"] == ["Backend Engineer"]
    assert body["profile"]["seniority_level"] == "senior"
    assert body["onboarding_complete"] is True


async def test_preferences_only_leaves_details_and_collections_intact(client, db, test_user):
    marker = uuid.uuid4().hex[:8]
    user_id = test_user.id
    await _seed_profile(db, user_id, first_name="Jane")
    await client.patch(
        "/api/v1/profile",
        json={
            "details": {
                "first_name": "Jane",
                "last_name": "Doe",
                "title": "Eng",
                "technologies": ["Python"],
                "employment_history": [{"company_name": f"PrefCo {marker}", "title": "Dev"}],
                "projects": [{"name": "Proj", "technologies": ["Rust"]}],
            }
        },
    )

    try:
        response = await client.patch("/api/v1/profile", json={"preferences": _PREFS})

        assert response.status_code == 200
        body = response.json()
        assert body["profile"]["first_name"] == "Jane"
        assert body["profile"]["title"] == "Eng"
        assert [e["company_name"] for e in body["employment_history"]] == [f"PrefCo {marker}"]
        assert [p["name"] for p in body["projects"]] == ["Proj"]
        assert body["projects"][0]["tech_stack"] == ["rust"]
        # Project-only tech is NOT hoisted into the profile's skill set on the
        # human path (process_cv unions them; the editor's list is user-curated).
        assert body["profile"]["technologies"] == ["python"]
        assert body["onboarding_complete"] is True
    finally:
        profile_id = await db.scalar(select(Profile.id).where(Profile.user_id == user_id))
        await db.execute(
            delete(EmploymentHistory).where(EmploymentHistory.profile_id == profile_id)
        )
        await db.execute(delete(Company).where(Company.name == f"PrefCo {marker}"))
        await db.commit()


async def test_both_sections_apply_in_one_request(client, db, test_user):
    await _seed_profile(db, test_user.id, first_name="Old")

    response = await client.patch(
        "/api/v1/profile",
        json={
            "details": {"first_name": "Jane", "last_name": "Doe", "title": "Eng"},
            "preferences": _PREFS,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["first_name"] == "Jane"
    assert body["profile"]["desired_roles"] == ["Backend Engineer"]
    assert body["onboarding_complete"] is True
    assert body["completion_issues"] == []


async def test_details_failure_rolls_back_the_preferences_in_the_same_request(
    client, db, test_user
):
    """The reason the two steps had to merge: one transaction, or none."""
    other = User(
        username=f"pytest-{uuid.uuid4().hex[:12]}",
        email=f"pytest-{uuid.uuid4().hex[:12]}@example.test",
    )
    db.add(other)
    await db.commit()
    await db.refresh(other)
    other_id = other.id

    await _seed_profile(db, test_user.id, first_name="Jane", **_PREFS)
    other_profile_id = await _seed_profile(db, other_id, with_resume=False)
    await projects.save_projects(db, other_profile_id, [ProjectEntry(name="Theirs")])
    await db.commit()
    [foreign] = await projects.load_projects(db, other_profile_id)

    try:
        response = await client.patch(
            "/api/v1/profile",
            json={
                "details": {
                    "first_name": "Jane",
                    "projects": [{"project_id": foreign.project_id, "name": "Stolen"}],
                },
                "preferences": {**_PREFS, "seniority_level": "lead"},
            },
        )

        assert response.status_code == 409
        # The preferences upsert ran BEFORE the ownership check failed, so this
        # only passes if both sections share one transaction.
        profile = (await client.get("/api/v1/profile")).json()["profile"]
        assert profile["seniority_level"] == "senior"
    finally:
        await db.execute(delete(User).where(User.id == other_id))
        await db.commit()


# ── Error envelope ─────────────────────────────────────────────────────


async def test_unhandled_error_returns_cors_safe_envelope(client, db, test_user, monkeypatch):
    """An uncaught exception returns the envelope with a request_id AND the CORS
    header (so the browser can read it), and never leaks internals."""
    from app.config import settings

    await _seed_profile(db, test_user.id)

    def boom(*args, **kwargs):
        raise RuntimeError("connection to postgres://secret failed")

    monkeypatch.setattr(profile_service, "get_snapshot", boom)
    origin = settings.cors_origins_list[0]
    response = await client.get("/api/v1/profile", headers={"Origin": origin})

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["request_id"]
    # CORS header present -> the browser won't drop this as a network failure.
    assert response.headers.get("access-control-allow-origin") == origin
    # No provider/exception internals in the response body.
    assert "postgres://secret" not in response.text
    assert "RuntimeError" not in response.text
