"""Profile onboarding orchestration and document-derived data persistence."""

import uuid
from collections.abc import Iterable

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import Profile
from app.models.project import ProfileProject, Project, ProjectSource
from app.models.resume import Resume
from app.models.technology import ProfileTechnology, Technology
from app.schemas.profile import CVExtraction, TechnologySelection
from app.schemas.project import ParsedProject, ProjectRead
from app.services import linkedin_extract, pdf, project_extract, resume_service, text_extract

_PROFILE_EXTRACTION_FIELDS = ("first_name", "last_name", "phone_number", "summary")


def normalize_technology(value: str) -> str:
    return " ".join(value.strip().casefold().split())


async def upsert_profile(db: AsyncSession, user_id: uuid.UUID, fields: dict) -> None:
    """Create the user's profile or update only the supplied fields."""
    statement = pg_insert(Profile).values(user_id=user_id, **fields)
    statement = statement.on_conflict_do_update(
        index_elements=[Profile.user_id],
        set_={**fields, "updated_at": func.now()},
    )
    await db.execute(statement)


async def _load_profile(db: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    return (
        await db.execute(
            select(Profile)
            .where(Profile.user_id == user_id)
            .options(selectinload(Profile.technologies).selectinload(ProfileTechnology.technology))
        )
    ).scalar_one_or_none()


async def _profile_id(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    profile_id = await db.scalar(select(Profile.profile_id).where(Profile.user_id == user_id))
    if profile_id is None:
        raise ValueError(f"Profile for user {user_id} does not exist")
    return profile_id


async def _merge_social_links(
    db: AsyncSession, user_id: uuid.UUID, links: dict[str, str | None]
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


async def _resolve_technology(db: AsyncSession, selection: TechnologySelection) -> Technology:
    if selection.technology_id is not None:
        technology = await db.get(Technology, selection.technology_id)
        if technology is None or not technology.is_active:
            raise ValueError(f"Unknown technology {selection.technology_id}")
        return technology

    assert selection.name is not None
    canonical_name = " ".join(selection.name.strip().split())
    normalized_name = normalize_technology(canonical_name)
    technology_id = uuid.uuid5(uuid.NAMESPACE_URL, f"hire-journey:technology:{normalized_name}")
    statement = (
        pg_insert(Technology)
        .values(
            technology_id=technology_id,
            canonical_name=canonical_name,
            normalized_name=normalized_name,
        )
        .on_conflict_do_update(
            index_elements=[Technology.normalized_name],
            set_={"normalized_name": normalized_name},
        )
        .returning(Technology)
    )
    return (await db.execute(statement)).scalar_one()


async def set_profile_technologies(
    db: AsyncSession,
    profile_id: uuid.UUID,
    selections: Iterable[TechnologySelection],
    *,
    replace: bool,
) -> None:
    if replace:
        await db.execute(
            delete(ProfileTechnology).where(ProfileTechnology.profile_id == profile_id)
        )

    for selection in selections:
        technology = await _resolve_technology(db, selection)
        values = {
            "profile_id": profile_id,
            "technology_id": technology.technology_id,
            "proficiency": selection.proficiency,
            "years_experience": selection.years_experience,
        }
        statement = pg_insert(ProfileTechnology).values(**values)
        if replace:
            statement = statement.on_conflict_do_update(
                index_elements=[
                    ProfileTechnology.profile_id,
                    ProfileTechnology.technology_id,
                ],
                set_={
                    "proficiency": selection.proficiency,
                    "years_experience": selection.years_experience,
                },
            )
        else:
            statement = statement.on_conflict_do_nothing(
                index_elements=[
                    ProfileTechnology.profile_id,
                    ProfileTechnology.technology_id,
                ]
            )
        await db.execute(statement)


def _project_read(project: Project, membership: ProfileProject) -> ProjectRead:
    return ProjectRead(
        project_id=project.project_id,
        name=project.name,
        summary=project.summary,
        tech_stack=project.tech_stack,
        github_url=project.github_url,
        deployed_url=project.deployed_url,
        project_start_date=project.start_date,
        project_end_date=project.end_date,
        role=membership.role,
        contribution_summary=membership.contribution_summary,
        participation_start_date=membership.start_date,
        participation_end_date=membership.end_date,
        is_current=membership.is_current,
        source=membership.source,
    )


async def _load_projects(
    db: AsyncSession, profile_id: uuid.UUID, source: str | None = None
) -> list[ProjectRead]:
    query = (
        select(Project, ProfileProject)
        .join(ProfileProject, ProfileProject.project_id == Project.project_id)
        .where(ProfileProject.profile_id == profile_id)
    )
    if source is not None:
        query = query.where(ProfileProject.source == source)
    rows = (await db.execute(query.order_by(ProfileProject.created_at))).all()
    return [_project_read(project, membership) for project, membership in rows]


async def replace_projects(
    db: AsyncSession,
    profile_id: uuid.UUID,
    projects: list[ParsedProject],
    source: str,
) -> None:
    """Replace one profile's source-scoped project memberships."""
    old_project_ids = list(
        (
            await db.scalars(
                select(ProfileProject.project_id).where(
                    ProfileProject.profile_id == profile_id,
                    ProfileProject.source == source,
                )
            )
        ).all()
    )
    await db.execute(
        delete(ProfileProject).where(
            ProfileProject.profile_id == profile_id,
            ProfileProject.source == source,
        )
    )
    if old_project_ids:
        await db.execute(
            delete(Project).where(
                Project.project_id.in_(old_project_ids),
                ~exists().where(ProfileProject.project_id == Project.project_id),
            )
        )

    for parsed in projects:
        project = Project(**parsed.model_dump())
        db.add(project)
        await db.flush()
        db.add(
            ProfileProject(
                profile_id=profile_id,
                project_id=project.project_id,
                source=source,
            )
        )


def _profile_values(extraction: CVExtraction) -> dict:
    values = {
        "first_name": extraction.first_name,
        "last_name": extraction.last_name,
        "phone_number": extraction.phone,
        "summary": extraction.summary,
    }
    return {field: values[field] for field in _PROFILE_EXTRACTION_FIELDS if values.get(field)}


async def get_profile(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[Profile, list[ProjectRead], str | None] | None:
    profile = await _load_profile(db, user_id)
    if profile is None:
        return None
    resume = (
        await db.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.is_active.is_(True))
        )
    ).scalar_one_or_none()
    resume_summary = (resume.parsed_content or {}).get("summary") if resume else None
    return profile, await _load_projects(db, profile.profile_id), resume_summary


async def update_profile(db: AsyncSession, user_id: uuid.UUID, fields: dict) -> Profile:
    technology_selections = fields.pop("technologies", None)
    try:
        await upsert_profile(db, user_id, fields)
        profile_id = await _profile_id(db, user_id)
        if technology_selections is not None:
            await set_profile_technologies(
                db,
                profile_id,
                [
                    item
                    if isinstance(item, TechnologySelection)
                    else TechnologySelection.model_validate(item)
                    for item in technology_selections
                ],
                replace=True,
            )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    profile = await _load_profile(db, user_id)
    assert profile is not None
    return profile


async def process_cv(
    db: AsyncSession,
    user_id: uuid.UUID,
    file_name: str,
    data: bytes,
    replace_resume_id: uuid.UUID | None = None,
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
                make_active=True,
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
        fields["source_resume_id"] = resume.resume_id
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
        await set_profile_technologies(
            db,
            profile_id,
            [TechnologySelection(name=name) for name in extraction.tech_stack],
            replace=False,
        )
        await replace_projects(db, profile_id, projects, ProjectSource.CV)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    profile = await _load_profile(db, user_id)
    assert profile is not None
    stored_projects = await _load_projects(db, profile.profile_id, ProjectSource.CV)
    return profile, stored_projects, extraction.summary


async def process_linkedin(db: AsyncSession, user_id: uuid.UUID, data: bytes) -> Profile:
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
        await set_profile_technologies(
            db,
            profile_id,
            [TechnologySelection(name=name) for name in extraction.tech_stack],
            replace=False,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    profile = await _load_profile(db, user_id)
    assert profile is not None
    return profile


async def process_projects_pdf(
    db: AsyncSession, user_id: uuid.UUID, data: bytes
) -> list[ProjectRead]:
    text_content = pdf.extract_text(data)
    projects = project_extract.extract_projects(text_content, section_only=False)

    try:
        await upsert_profile(db, user_id, {})
        profile_id = await _profile_id(db, user_id)
        await replace_projects(db, profile_id, projects, ProjectSource.PROJECTS_PDF)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await _load_projects(db, profile_id, ProjectSource.PROJECTS_PDF)
