"""Profile onboarding orchestration and resume-derived data persistence."""

from collections.abc import Iterable
from datetime import date

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import messages
from app.exceptions import ProfileNotFoundError, ProjectOwnershipError
from app.models.company import Company
from app.models.employment import EmploymentHistory
from app.models.profile import Profile
from app.models.project import ProfileProject, ProfileProjectTechnology, Project
from app.models.resume import Resume
from app.models.technology import ProfileTechnology, Technology
from app.schemas.extraction import EmploymentItem, ProjectItem, ResumeExtraction
from app.schemas.profile import (
    CompletionIssue,
    EmploymentEntry,
    EmploymentRead,
    PreferencesUpdate,
    ProfileDetailsUpdate,
    ProjectEntry,
    ResumeMeta,
)
from app.schemas.project import ProjectRead
from app.services import resume_service
from app.utils import document_parser, llm, normalization, prompts


def normalize_technology(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _clean(value: str | None) -> str | None:
    """Trimmed string, with blank collapsing to None."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def _clip(value: str | None, limit: int) -> str | None:
    """Lenient-path guard: LLM output is unbounded but the columns are not.

    Truncates instead of erroring — a 500 on a valid resume is worse than a
    shortened value the user can fix in the editor.
    """
    cleaned = _clean(value)
    return cleaned[:limit] if cleaned else None


async def upsert_profile(db: AsyncSession, user_id: int, fields: dict) -> None:
    """Create the user's profile or update only the supplied fields."""
    statement = pg_insert(Profile).values(user_id=user_id, **fields)
    statement = statement.on_conflict_do_update(
        index_elements=[Profile.user_id],
        set_={**fields, "updated_at": func.now()},
    )
    await db.execute(statement)


async def _load_profile(db: AsyncSession, user_id: int) -> Profile | None:
    return (
        await db.execute(
            select(Profile)
            .where(Profile.user_id == user_id)
            .options(selectinload(Profile.technologies).selectinload(ProfileTechnology.technology))
            # The profile is written via Core statements (upsert), which bypass
            # the ORM identity map; with expire_on_commit=False a previously
            # loaded instance would otherwise be returned with stale attributes.
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()


async def _profile_id(db: AsyncSession, user_id: int) -> int:
    profile_id = await db.scalar(select(Profile.id).where(Profile.user_id == user_id))
    if profile_id is None:
        raise ProfileNotFoundError(messages.PROFILE_NOT_FOUND)
    return profile_id


def onboarding_completion_issues(profile: Profile) -> list[CompletionIssue]:
    """Return every unmet onboarding requirement in step order."""
    issues: list[CompletionIssue] = []
    requirements = (
        (
            profile.source_resume_id is not None,
            "profile",
            ["source_resume"],
            "Upload a resume.",
        ),
        (
            bool(_clean(profile.first_name)),
            "profile",
            ["first_name"],
            "Enter your first name.",
        ),
        (
            bool(_clean(profile.last_name)),
            "profile",
            ["last_name"],
            "Enter your last name.",
        ),
        (
            bool(_clean(profile.title)),
            "profile",
            ["title"],
            "Enter your professional title.",
        ),
        (
            bool(profile.desired_roles),
            "preferences",
            ["desired_roles"],
            "Add at least one desired role.",
        ),
        (
            bool(profile.desired_locations),
            "preferences",
            ["desired_locations"],
            "Add at least one desired location.",
        ),
        (
            bool(profile.work_modes_preferred),
            "preferences",
            ["work_modes_preferred"],
            "Pick at least one work mode.",
        ),
        (
            bool(_clean(profile.seniority_level)),
            "preferences",
            ["seniority_level"],
            "Pick your seniority level.",
        ),
    )
    for complete, step, path, message in requirements:
        if not complete:
            issues.append(CompletionIssue(step=step, path=path, message=message))
    return issues


def is_onboarding_complete(profile: Profile) -> bool:
    """The computed completion rule — intentionally never persisted."""
    return not onboarding_completion_issues(profile)


async def _get_or_create_technology(db: AsyncSession, name: str) -> Technology:
    """Upsert a technology by its lowercase-normalized name."""
    normalized = normalize_technology(name)[:100]  # column limit; LLM output is unbounded
    statement = (
        pg_insert(Technology)
        .values(name=normalized)
        .on_conflict_do_update(index_elements=[Technology.name], set_={"name": normalized})
        .returning(Technology)
    )
    return (await db.execute(statement)).scalar_one()


async def set_profile_technologies(
    db: AsyncSession,
    profile_id: int,
    names: Iterable[str],
    *,
    replace: bool,
) -> None:
    if replace:
        await db.execute(
            delete(ProfileTechnology).where(ProfileTechnology.profile_id == profile_id)
        )
    for name in names:
        if not name.strip():
            continue
        technology = await _get_or_create_technology(db, name)
        statement = (
            pg_insert(ProfileTechnology)
            .values(profile_id=profile_id, technology_id=technology.id)
            .on_conflict_do_nothing(
                index_elements=[ProfileTechnology.profile_id, ProfileTechnology.technology_id]
            )
        )
        await db.execute(statement)


# ── Companies & employment ─────────────────────────────────────────────


def _normalize_company_name(name: str) -> str:
    """Collapse whitespace runs, preserving the display casing."""
    return " ".join(name.split())


async def _get_or_create_company(db: AsyncSession, display_name: str) -> Company:
    """Case-insensitively reuse a company row, creating it if absent.

    The database unique constraint covers only exact names, so "Google" and
    "google" would both pass. A transaction-scoped advisory lock keyed on the
    lowercase name serializes concurrent first-inserts instead. Callers resolve
    companies in sorted-name order so two uploads never acquire overlapping
    locks in opposite order.
    """
    key = display_name.lower()
    await db.execute(select(func.pg_advisory_xact_lock(func.hashtext(key))))
    company = (
        await db.execute(
            select(Company)
            .where(func.lower(Company.name) == key)
            # Deterministic compatibility rule: prefer a source-linked row,
            # then the oldest employer record.
            .order_by(Company.slug.is_(None), Company.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if company is not None:
        return company
    company = Company(name=display_name)
    db.add(company)
    await db.flush()
    return company


def _employment_dates(
    entry: EmploymentItem | EmploymentEntry,
) -> tuple[date | None, date | None]:
    start = normalization.normalize_month(entry.start_date)
    end = normalization.normalize_month(entry.end_date)
    if start and end and end < start:
        # Contradictory order: treat both as unparseable rather than guessing
        # (a null end alone would falsely mark the stint as current).
        return None, None
    return start, end


async def replace_employments(
    db: AsyncSession, profile_id: int, entries: list[EmploymentItem] | list[EmploymentEntry]
) -> None:
    """Replace the profile's employment rows.

    Deletes employment rows only. Company identity is shared across profiles
    and is never deleted here (unlike projects, which can be profile-owned).
    """
    await db.execute(delete(EmploymentHistory).where(EmploymentHistory.profile_id == profile_id))
    valid = [entry for entry in entries if _clean(entry.company_name) and _clean(entry.title)]
    display_names: dict[str, str] = {}
    for entry in valid:
        display = _clip(_normalize_company_name(entry.company_name), 255)
        display_names.setdefault(display.lower(), display)
    companies = {
        key: await _get_or_create_company(db, display_names[key])
        for key in sorted(display_names)  # sorted: consistent advisory-lock order
    }
    seen: set[tuple] = set()
    for entry in valid:
        start_date, end_date = _employment_dates(entry)
        company_key = _clip(_normalize_company_name(entry.company_name), 255).lower()
        title = _clip(entry.title, 255)
        # Resumes often repeat a stint (e.g. summary + history); keep the first.
        row_key = (company_key, title.lower(), start_date, end_date)
        if row_key in seen:
            continue
        seen.add(row_key)
        db.add(
            EmploymentHistory(
                profile_id=profile_id,
                company_id=companies[company_key].id,
                title=title,
                start_date=start_date,
                end_date=end_date,
                description=_clean(entry.description),
            )
        )
    await db.flush()


# ── Projects ───────────────────────────────────────────────────────────


def _project_read(membership: ProfileProject, project: Project) -> ProjectRead:
    return ProjectRead(
        project_id=project.id,
        name=project.name,
        summary=membership.summary,
        tech_stack=[link.technology.name for link in membership.technologies],
        github_url=membership.github_url,
        deployed_url=membership.deployed_url,
    )


async def _load_memberships(
    db: AsyncSession, profile_id: int
) -> list[tuple[ProfileProject, Project]]:
    rows = (
        await db.execute(
            select(ProfileProject, Project)
            .join(Project, Project.id == ProfileProject.project_id)
            .where(ProfileProject.profile_id == profile_id)
            .options(
                selectinload(ProfileProject.technologies).selectinload(
                    ProfileProjectTechnology.technology
                )
            )
            .order_by(ProfileProject.created_at)
        )
    ).all()
    return [(membership, project) for membership, project in rows]


async def _load_projects(db: AsyncSession, profile_id: int) -> list[ProjectRead]:
    return [
        _project_read(membership, project)
        for membership, project in await _load_memberships(db, profile_id)
    ]


async def _set_membership_technologies(
    db: AsyncSession, profile_project_id: int, names: Iterable[str]
) -> None:
    await db.execute(
        delete(ProfileProjectTechnology).where(
            ProfileProjectTechnology.profile_project_id == profile_project_id
        )
    )
    for name in names:
        if not name.strip():
            continue
        technology = await _get_or_create_technology(db, name)
        await db.execute(
            pg_insert(ProfileProjectTechnology)
            .values(profile_project_id=profile_project_id, technology_id=technology.id)
            .on_conflict_do_nothing(
                index_elements=[
                    ProfileProjectTechnology.profile_project_id,
                    ProfileProjectTechnology.technology_id,
                ]
            )
        )


def _project_url(value: str | None) -> str | None:
    """Normalized URL, dropped when malformed or over the column limit."""
    url = normalization.normalize_url(value)
    return url if url and len(url) <= 255 else None


async def _create_membership(
    db: AsyncSession, profile_id: int, parsed: ProjectItem | ProjectEntry
) -> None:
    project = Project(name=_clip(parsed.name, 255))
    db.add(project)
    await db.flush()
    membership = ProfileProject(
        profile_id=profile_id,
        project_id=project.id,
        summary=_clean(parsed.summary),
        github_url=_project_url(parsed.github_url),
        deployed_url=_project_url(parsed.deployed_url),
    )
    db.add(membership)
    await db.flush()
    await _set_membership_technologies(db, membership.id, parsed.technologies)


async def replace_projects(db: AsyncSession, profile_id: int, projects: list[ProjectItem]) -> None:
    """Replace a profile's project memberships and remove unreferenced projects."""
    old_project_ids = list(
        (
            await db.scalars(
                select(ProfileProject.project_id).where(ProfileProject.profile_id == profile_id)
            )
        ).all()
    )
    await db.execute(delete(ProfileProject).where(ProfileProject.profile_id == profile_id))
    if old_project_ids:
        await db.execute(
            delete(Project).where(
                Project.id.in_(old_project_ids),
                ~exists().where(ProfileProject.project_id == Project.id),
            )
        )
    # The LLM can surface the same project from two resume sections; dedupe
    # by normalized name (first occurrence wins) so one profile never gets
    # duplicate identities from a single extraction.
    seen_names: set[str] = set()
    for parsed in projects:
        name = _clean(parsed.name)
        if not name:
            continue
        key = " ".join(name.lower().split())
        if key in seen_names:
            continue
        seen_names.add(key)
        await _create_membership(db, profile_id, parsed)


# ── Resume upload orchestration ────────────────────────────────────────


def _resume_profile_values(extraction: ResumeExtraction) -> dict:
    """Map an extraction onto profile columns.

    Every resume-derived key is always present, so a re-upload overwrites
    stale values — clearing ones the new resume no longer contains. The
    preference fields are never touched. Education/certification entries
    without their required field are dropped here but survive verbatim in
    resumes.parsed_content.
    """
    social_links = {
        key: normalization.normalize_url(value)
        for key, value in {
            "github_url": extraction.github_url,
            "linkedin_url": extraction.linkedin_url,
            "portfolio_url": extraction.portfolio_url,
        }.items()
    }
    return {
        "first_name": _clip(extraction.first_name, 100),
        "last_name": _clip(extraction.last_name, 100),
        "phone_number": _clip(extraction.phone_number, 50),
        "location": _clip(extraction.location, 255),
        "title": _clip(extraction.title, 255),
        "summary": _clean(extraction.summary),
        "social_links": {key: value for key, value in social_links.items() if value},
        "education": [
            item.model_dump(mode="json")
            for item in extraction.education
            if _clean(item.institution)
        ],
        "certifications": [
            item.model_dump(mode="json") for item in extraction.certifications if _clean(item.name)
        ],
    }


async def _load_employments(db: AsyncSession, profile_id: int) -> list[EmploymentRead]:
    rows = (
        await db.execute(
            select(EmploymentHistory, Company)
            .join(Company, Company.id == EmploymentHistory.company_id)
            .where(EmploymentHistory.profile_id == profile_id)
            .order_by(EmploymentHistory.start_date.desc().nulls_last(), EmploymentHistory.id)
        )
    ).all()
    return [
        EmploymentRead(
            id=employment.id,
            company_name=company.name,
            title=employment.title,
            start_date=employment.start_date,
            end_date=employment.end_date,
            description=employment.description,
        )
        for employment, company in rows
    ]


async def _source_resume_meta(db: AsyncSession, profile: Profile) -> ResumeMeta | None:
    if profile.source_resume_id is None:
        return None
    resume = await db.get(Resume, profile.source_resume_id)
    if resume is None:
        return None
    return ResumeMeta(
        id=resume.id,
        file_name=resume.file_name,
        created_at=resume.created_at,
        summary=(resume.parsed_content or {}).get("summary"),
    )


async def get_snapshot(
    db: AsyncSession, user_id: int
) -> tuple[Profile, ResumeMeta | None, list[EmploymentRead], list[ProjectRead]] | None:
    """Everything the onboarding UI needs, or None when no profile exists."""
    profile = await _load_profile(db, user_id)
    if profile is None:
        return None
    return (
        profile,
        await _source_resume_meta(db, profile),
        await _load_employments(db, profile.id),
        await _load_projects(db, profile.id),
    )


async def save_projects(db: AsyncSession, profile_id: int, entries: list[ProjectEntry]) -> None:
    """Reconcile the profile's projects against the edited full set.

    project_id present -> edit (must belong to this profile); absent -> new
    identity. Renaming a project shared with another profile copies-on-write
    instead of mutating it. Omitted memberships are removed, and projects
    left with no memberships are deleted.
    """
    memberships = {
        project.id: (membership, project)
        for membership, project in await _load_memberships(db, profile_id)
    }
    for row_index, entry in enumerate(entries):
        if entry.project_id is not None and entry.project_id not in memberships:
            raise ProjectOwnershipError(messages.PROJECT_NOT_OWNED, row_index)

    handled: set[int] = set()
    for entry in entries:
        if entry.project_id is None:
            await _create_membership(db, profile_id, entry)
            continue
        membership, project = memberships[entry.project_id]
        handled.add(entry.project_id)
        name = entry.name.strip()
        shared = bool(
            await db.scalar(
                select(func.count())
                .select_from(ProfileProject)
                .where(
                    ProfileProject.project_id == project.id,
                    ProfileProject.id != membership.id,
                )
            )
        )
        if shared and name != project.name:
            # Copy-on-write: never rename a project another profile references.
            await db.delete(membership)
            await db.flush()
            await _create_membership(db, profile_id, entry)
            continue
        project.name = name
        membership.summary = _clean(entry.summary)
        membership.github_url = entry.github_url
        membership.deployed_url = entry.deployed_url
        await db.flush()
        await _set_membership_technologies(db, membership.id, entry.technologies)

    for project_id in sorted(set(memberships) - handled):
        membership, project = memberships[project_id]
        await db.delete(membership)
        await db.flush()
        remaining = await db.scalar(
            select(func.count())
            .select_from(ProfileProject)
            .where(ProfileProject.project_id == project_id)
        )
        if not remaining:
            await db.delete(project)
    await db.flush()


async def save_details(db: AsyncSession, user_id: int, details: ProfileDetailsUpdate) -> None:
    """Atomically persist the corrected details step (full replacement)."""
    try:
        profile_id = await _profile_id(db, user_id)  # 404 before any writes
        links = {
            "github_url": details.social_links.github_url,
            "linkedin_url": details.social_links.linkedin_url,
            "portfolio_url": details.social_links.portfolio_url,
        }
        fields = {
            "first_name": _clean(details.first_name),
            "last_name": _clean(details.last_name),
            "phone_number": _clean(details.phone_number),
            "location": _clean(details.location),
            "title": _clean(details.title),
            "summary": _clean(details.summary),
            "social_links": {key: value for key, value in links.items() if value},
            "education": [entry.model_dump(mode="json") for entry in details.education],
            "certifications": [entry.model_dump(mode="json") for entry in details.certifications],
        }
        await upsert_profile(db, user_id, fields)
        await set_profile_technologies(db, profile_id, details.technologies, replace=True)
        await replace_employments(db, profile_id, details.employment_history)
        await save_projects(db, profile_id, details.projects)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def save_preferences(db: AsyncSession, user_id: int, preferences: PreferencesUpdate) -> None:
    """Persist the preferences step (onboarding must have started)."""
    try:
        await _profile_id(db, user_id)  # 404 before any writes
        await upsert_profile(
            db,
            user_id,
            {
                "minimum_salary": preferences.minimum_salary,
                "desired_roles": preferences.desired_roles,
                "desired_locations": preferences.desired_locations,
                "work_modes_preferred": list(preferences.work_modes_preferred),
                "seniority_level": preferences.seniority_level,
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def update_profile(db: AsyncSession, user_id: int, fields: dict) -> Profile:
    technology_names = fields.pop("technologies", None)
    try:
        await upsert_profile(db, user_id, fields)
        profile_id = await _profile_id(db, user_id)
        if technology_names is not None:
            await set_profile_technologies(db, profile_id, technology_names, replace=True)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    profile = await _load_profile(db, user_id)
    assert profile is not None
    return profile


async def process_cv(
    db: AsyncSession,
    user_id: int,
    file_name: str,
    data: bytes,
    replace_resume_id: int | None = None,
) -> tuple[Profile, list[ProjectRead], str | None]:
    """Parse a resume, LLM-extract it, and persist everything in one transaction."""
    # Parsing and extraction run BEFORE any DB writes: the LLM call takes
    # seconds and must never execute while holding the user row lock.
    text_content = document_parser.to_text(data, file_name)
    extraction = await llm.structured_extract(
        prompts.RESUME_EXTRACTION_SYSTEM, text_content, ResumeExtraction
    )
    # The raw, un-normalized extraction is preserved verbatim; persistence
    # below normalizes and filters, but nothing is lost.
    parsed_content = extraction.model_dump(mode="json")

    try:
        if replace_resume_id is None:
            resume = await resume_service.create_resume(
                db,
                user_id=user_id,
                file_name=file_name,
                raw_content=text_content,
                parsed_content=parsed_content,
            )
        else:
            resume = await resume_service.replace_resume(
                db,
                user_id=user_id,
                resume_id=replace_resume_id,
                file_name=file_name,
                raw_content=text_content,
                parsed_content=parsed_content,
            )

        fields = _resume_profile_values(extraction)
        fields["source_resume_id"] = resume.id
        await upsert_profile(db, user_id, fields)
        profile_id = await _profile_id(db, user_id)
        # profile_technologies is the candidate's overall skill set, so it must
        # be a superset of every project's tech — the LLM fills the top-level
        # and per-project lists independently, so union them here rather than
        # trusting it to hoist project-only tech up itself. (Order-stable
        # de-dup; _get_or_create_technology normalizes casing on top of this.)
        overall_technologies = list(
            dict.fromkeys(
                extraction.technologies
                + [tech for project in extraction.projects for tech in project.technologies]
            )
        )
        await set_profile_technologies(db, profile_id, overall_technologies, replace=True)
        await replace_employments(db, profile_id, extraction.employment_history)
        await replace_projects(db, profile_id, extraction.projects)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    profile = await _load_profile(db, user_id)
    assert profile is not None
    projects = await _load_projects(db, profile.id)
    return profile, projects, extraction.summary
