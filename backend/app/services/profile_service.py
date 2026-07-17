"""Profile onboarding orchestration and document-derived data persistence."""

from collections.abc import Iterable

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import Profile
from app.models.project import ProfileProject, ProfileProjectTechnology, Project
from app.models.resume import Resume
from app.models.technology import ProfileTechnology, Technology
from app.schemas.profile import CVExtraction
from app.schemas.project import ParsedProject, ProjectRead
from app.services import linkedin_extract, pdf, project_extract, resume_service, text_extract

_PROFILE_EXTRACTION_FIELDS = (
    "first_name",
    "last_name",
    "phone_number",
    "summary",
)


def normalize_technology(value: str) -> str:
    return " ".join(value.strip().casefold().split())


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
        )
    ).scalar_one_or_none()


async def _profile_id(db: AsyncSession, user_id: int) -> int:
    profile_id = await db.scalar(select(Profile.id).where(Profile.user_id == user_id))
    if profile_id is None:
        raise ValueError(f"Profile for user {user_id} does not exist")
    return profile_id


async def _merge_social_links(
    db: AsyncSession, user_id: int, links: dict[str, str | None]
) -> None:
    clean_links = {key: value for key, value in links.items() if value}
    if not clean_links:
        return
    await db.execute(
        update(Profile)
        .where(Profile.user_id == user_id)
        .values(
            social_links=Profile.social_links.op("||")(clean_links),
            updated_at=func.now(),
        )
    )


async def _get_or_create_technology(db: AsyncSession, name: str) -> Technology:
    """Upsert a technology by its lowercase-normalized name."""
    normalized = normalize_technology(name)
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


async def _create_membership(
    db: AsyncSession, profile_id: int, parsed: ParsedProject
) -> None:
    project = Project(name=parsed.name)
    db.add(project)
    await db.flush()
    membership = ProfileProject(
        profile_id=profile_id,
        project_id=project.id,
        summary=parsed.summary,
        github_url=parsed.github_url,
        deployed_url=parsed.deployed_url,
    )
    db.add(membership)
    await db.flush()
    await _set_membership_technologies(db, membership.id, parsed.tech_stack)


async def replace_projects(
    db: AsyncSession, profile_id: int, projects: list[ParsedProject]
) -> None:
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
    for parsed in projects:
        await _create_membership(db, profile_id, parsed)


def _profile_values(extraction: CVExtraction) -> dict:
    values = {
        "first_name": extraction.first_name,
        "last_name": extraction.last_name,
        "phone_number": extraction.phone,
        "summary": extraction.summary,
    }
    return {field: values[field] for field in _PROFILE_EXTRACTION_FIELDS if values.get(field)}


async def _latest_resume(db: AsyncSession, user_id: int) -> Resume | None:
    return (
        await db.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def get_profile(
    db: AsyncSession, user_id: int
) -> tuple[Profile, list[ProjectRead], str | None] | None:
    profile = await _load_profile(db, user_id)
    if profile is None:
        return None
    resume = await _latest_resume(db, user_id)
    resume_summary = (resume.parsed_content or {}).get("summary") if resume else None
    projects = await _load_projects(db, profile.id)
    return profile, projects, resume_summary


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
    text_content = pdf.extract_text(data)
    extraction = text_extract.extract_fields(text_content)
    projects = project_extract.extract_projects(text_content)
    parsed_content = {
        **extraction.model_dump(mode="json"),
        "projects": [project.model_dump(mode="json") for project in projects],
    }

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

        fields = _profile_values(extraction)
        fields["source_resume_id"] = resume.id
        await upsert_profile(db, user_id, fields)
        await _merge_social_links(
            db,
            user_id,
            {
                "linkedin_url": extraction.linkedin_url,
                "github_url": extraction.github_url,
            },
        )
        profile_id = await _profile_id(db, user_id)
        await set_profile_technologies(db, profile_id, extraction.tech_stack, replace=False)
        await replace_projects(db, profile_id, projects)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    profile = await _load_profile(db, user_id)
    assert profile is not None
    projects = await _load_projects(db, profile.id)
    return profile, projects, extraction.summary


async def process_linkedin(db: AsyncSession, user_id: int, data: bytes) -> Profile:
    text_content = pdf.extract_text(data)
    extraction = linkedin_extract.extract_fields(text_content)
    fields = {
        key: value
        for key, value in {
            "first_name": extraction.first_name,
            "last_name": extraction.last_name,
            "phone_number": extraction.phone,
        }.items()
        if value
    }

    try:
        await upsert_profile(db, user_id, fields)
        await _merge_social_links(db, user_id, {"linkedin_url": extraction.linkedin_url})
        profile_id = await _profile_id(db, user_id)
        await set_profile_technologies(db, profile_id, extraction.tech_stack, replace=False)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    profile = await _load_profile(db, user_id)
    assert profile is not None
    return profile


async def process_projects_pdf(
    db: AsyncSession, user_id: int, data: bytes
) -> list[ProjectRead]:
    text_content = pdf.extract_text(data)
    projects = project_extract.extract_projects(text_content, section_only=False)

    try:
        await upsert_profile(db, user_id, {})
        profile_id = await _profile_id(db, user_id)
        await replace_projects(db, profile_id, projects)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await _load_projects(db, profile_id)
