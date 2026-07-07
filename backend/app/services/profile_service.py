"""Candidate orchestration: parse a document, extract fields, and persist them."""

import uuid

import anyio
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.project import Project, ProjectSource
from app.models.resume import Resume
from app.schemas.profile import ResumeExtraction
from app.schemas.project import ParsedProject
from app.utils import document_parser, llm, prompts

_CANDIDATE_FIELDS = (
    "first_name", "last_name", "email", "phone", "github_url", "portfolio_url",
)


async def upsert_candidate(db: AsyncSession, user_id: uuid.UUID, fields: dict) -> None:
    """Insert or update a candidate, touching only the provided fields.

    Columns absent from ``fields`` keep their existing values, so each upload
    augments the candidate instead of overwriting it.
    """
    statement = pg_insert(Candidate).values(user_id=user_id, **fields).on_conflict_do_update(
        index_elements=[Candidate.user_id],
        set_={**fields, "updated_at": func.now()},
    )
    await db.execute(statement)


async def update_candidate(
    db: AsyncSession, user_id: uuid.UUID, fields: dict
) -> Candidate:
    """Persist a partial candidate update and return the refreshed row."""
    await upsert_candidate(db, user_id, fields)
    await db.commit()
    return (
        await db.execute(select(Candidate).where(Candidate.user_id == user_id))
    ).scalar_one()


async def _load_cv_projects(db: AsyncSession, user_id: uuid.UUID) -> list[Project]:
    """Return the user's CV-sourced projects, oldest first."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id, Project.source == ProjectSource.CV)
        .order_by(Project.created_at)
    )
    return list(result.scalars().all())


async def get_profile(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[Candidate, list[Project], str | None] | None:
    """Load the candidate with its active-resume summary and CV projects, or None if absent."""
    candidate = (
        await db.execute(select(Candidate).where(Candidate.user_id == user_id))
    ).scalar_one_or_none()
    if candidate is None:
        return None
    resume = (
        await db.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.is_active.is_(True))
        )
    ).scalar_one_or_none()
    summary = (resume.parsed_content or {}).get("summary") if resume else None
    return candidate, await _load_cv_projects(db, user_id), summary


async def set_projects(
    db: AsyncSession, user_id: uuid.UUID, projects: list[ParsedProject]
) -> list[Project]:
    """Replace the user's CV-sourced projects with the provided set and return them."""
    await replace_projects(db, user_id, projects, ProjectSource.CV)
    await db.commit()
    return await _load_cv_projects(db, user_id)


async def replace_projects(
    db: AsyncSession, user_id: uuid.UUID, projects: list[ParsedProject], source: str
) -> None:
    """Swap in a source's projects: drop its previous rows, insert the new set."""
    await db.execute(
        delete(Project).where(Project.user_id == user_id, Project.source == source)
    )
    db.add_all(
        Project(user_id=user_id, source=source, **project.model_dump())
        for project in projects
    )


def _candidate_values(extraction: ResumeExtraction) -> dict:
    data = extraction.model_dump()
    fields = {name: data[name] for name in _CANDIDATE_FIELDS if data.get(name)}
    if extraction.skills:
        fields["tech_stack"] = extraction.skills
    return fields


async def process_cv(
    db: AsyncSession, user_id: uuid.UUID, file_name: str, data: bytes
) -> tuple[Candidate, list[Project], str | None]:
    """Parse a CV, extract structured fields, and persist across resume, candidate, and project tables.

    Parsing and extraction run before any write; the resume insert, candidate upsert, and
    project replacement share one transaction so all three commit together or not at all.
    """
    text = await anyio.to_thread.run_sync(document_parser.to_text, data, file_name)
    extraction = await llm.structured_extract(
        prompts.RESUME_EXTRACTION_SYSTEM, text, ResumeExtraction
    )

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
            parsed_content=extraction.model_dump(),
            is_active=True,
        )
        db.add(resume)
        await db.flush()

        fields = _candidate_values(extraction)
        fields["source_resume_id"] = resume.resume_id
        await upsert_candidate(db, user_id, fields)
        await replace_projects(db, user_id, extraction.projects, ProjectSource.CV)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    candidate = (
        await db.execute(select(Candidate).where(Candidate.user_id == user_id))
    ).scalar_one()
    return candidate, await _load_cv_projects(db, user_id), extraction.summary
