"""Profile orchestration: parse a CV, persist it, and fan out to the tables."""

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectSource
from app.models.resume import Resume
from app.models.user_profile import UserProfile
from app.schemas.profile import CVExtraction
from app.schemas.project import ParsedProject
from app.services import pdf, project_extract, text_extract

_PROFILE_FIELDS = (
    "first_name", "last_name", "email", "phone", "linkedin_url", "github_url", "tech_stack",
)


async def upsert_profile(db: AsyncSession, user_id: uuid.UUID, fields: dict) -> None:
    """Insert or update a profile, touching only the provided fields.

    Reused by every source: columns absent from ``fields`` keep their existing
    values, so each upload augments the profile instead of overwriting it.
    """
    statement = pg_insert(UserProfile).values(user_id=user_id, **fields).on_conflict_do_update(
        index_elements=[UserProfile.user_id],
        set_={**fields, "updated_at": func.now()},
    )
    await db.execute(statement)


async def replace_projects(
    db: AsyncSession, user_id: uuid.UUID, projects: list[ParsedProject], source: str
) -> None:
    """Swap in a source's projects: drop its previous rows, insert the new set.

    Source-scoped so the CV and projects-PDF endpoints never clobber each other.
    """
    await db.execute(
        delete(Project).where(Project.user_id == user_id, Project.source == source)
    )
    db.add_all(
        Project(user_id=user_id, source=source, **project.model_dump())
        for project in projects
    )


def _profile_values(extraction: CVExtraction) -> dict:
    data = extraction.model_dump()
    return {field: data[field] for field in _PROFILE_FIELDS if data.get(field)}


async def process_cv(
    db: AsyncSession, user_id: uuid.UUID, file_name: str, data: bytes
) -> tuple[UserProfile, list[Project], str | None]:
    """Parse a CV and persist it across the resume, profile, and project tables.

    Parsing runs before any write; the resume insert, profile upsert, and project
    replacement share one transaction so all three commit together or not at all.
    """
    text = pdf.extract_text(data)
    extraction = text_extract.extract_fields(text)
    projects = project_extract.extract_projects(text)
    parsed_content = {
        **extraction.model_dump(),
        "projects": [project.model_dump() for project in projects],
    }

    try:
        await db.execute(
            update(Resume)
            .where(Resume.user_id == user_id, Resume.is_active.is_(True))
            .values(is_active=False)
        )
        resume = Resume(
            user_id=user_id,
            file_name=file_name,
            raw_content=text,
            parsed_content=parsed_content,
            is_active=True,
        )
        db.add(resume)
        await db.flush()

        fields = _profile_values(extraction)
        fields["source_resume_id"] = resume.resume_id
        await upsert_profile(db, user_id, fields)
        await replace_projects(db, user_id, projects, ProjectSource.CV)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one()
    stored_projects = (
        await db.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.source == ProjectSource.CV)
            .order_by(Project.created_at)
        )
    ).scalars().all()
    return profile, list(stored_projects), extraction.summary
