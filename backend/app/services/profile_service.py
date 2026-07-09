"""Candidate orchestration: parse a document, persist it, and fan out to the tables."""

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.project import Project, ProjectSource
from app.models.resume import Resume
from app.schemas.profile import CVExtraction
from app.schemas.project import ParsedProject, ProjectInput
from app.services import pdf, project_extract, text_extract

_CANDIDATE_FIELDS = (
    "first_name", "last_name", "email", "phone", "github_url", "tech_stack", "summary",
)


async def _get_candidate(db: AsyncSession, user_id: uuid.UUID) -> Candidate | None:
    """Return the user's candidate row, or None when they have no profile yet."""
    return (
        await db.execute(select(Candidate).where(Candidate.user_id == user_id))
    ).scalar_one_or_none()


async def _list_projects(
    db: AsyncSession, user_id: uuid.UUID, source: str | None = None
) -> list[Project]:
    """Return the user's projects (all sources, or one) ordered oldest-first."""
    query = select(Project).where(Project.user_id == user_id)
    if source is not None:
        query = query.where(Project.source == source)
    return list((await db.execute(query.order_by(Project.created_at))).scalars().all())


async def upsert_candidate(db: AsyncSession, user_id: uuid.UUID, fields: dict) -> None:
    """Insert or update a candidate, touching only the provided fields.

    Reused by every source: columns absent from ``fields`` keep their existing
    values, so each upload augments the candidate instead of overwriting it.
    """
    statement = pg_insert(Candidate).values(user_id=user_id, **fields).on_conflict_do_update(
        index_elements=[Candidate.user_id],
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


def _candidate_values(extraction: CVExtraction) -> dict:
    data = extraction.model_dump()
    return {field: data[field] for field in _CANDIDATE_FIELDS if data.get(field)}


async def get_snapshot(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[Candidate | None, list[Project], str | None]:
    """Load the persisted onboarding state so a returning user resumes where they left off.

    Returns ``(candidate, projects, summary)`` — or ``(None, [], None)`` when the
    user has no candidate yet, which the endpoint surfaces as a 404.
    """
    candidate = await _get_candidate(db, user_id)
    if candidate is None:
        return None, [], None
    projects = await _list_projects(db, user_id)
    return candidate, projects, candidate.summary


async def update_profile(db: AsyncSession, user_id: uuid.UUID, fields: dict) -> Candidate:
    """Partially update the candidate with ``fields`` and return the fresh row.

    Backs both onboarding steps; an empty ``fields`` dict is a no-op touch.
    """
    await upsert_candidate(db, user_id, fields)
    await db.commit()
    candidate = await _get_candidate(db, user_id)
    assert candidate is not None
    return candidate


async def set_projects(
    db: AsyncSession, user_id: uuid.UUID, projects: list[ProjectInput]
) -> list[Project]:
    """Replace the user's entire project set with the edited list and return it.

    Unlike :func:`replace_projects`, this spans all sources — the client sends the
    full edited set (CV + projects-PDF), so edits, deletions, and per-item source
    all persist in one write.
    """
    try:
        await db.execute(delete(Project).where(Project.user_id == user_id))
        db.add_all(Project(user_id=user_id, **project.model_dump()) for project in projects)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return await _list_projects(db, user_id)


async def process_cv(
    db: AsyncSession, user_id: uuid.UUID, file_name: str, data: bytes
) -> tuple[Candidate, list[Project], str | None]:
    """Parse a CV and persist it across the resume, candidate, and project tables.

    Parsing runs before any write; the resume insert, candidate upsert, and project
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

        fields = _candidate_values(extraction)
        fields["source_resume_id"] = resume.resume_id
        await upsert_candidate(db, user_id, fields)
        await replace_projects(db, user_id, projects, ProjectSource.CV)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    candidate = await _get_candidate(db, user_id)
    assert candidate is not None
    # All sources, so a re-upload keeps any projects added from a projects PDF.
    stored_projects = await _list_projects(db, user_id)
    return candidate, stored_projects, candidate.summary


async def process_projects_pdf(
    db: AsyncSession, user_id: uuid.UUID, data: bytes
) -> list[Project]:
    """Parse a projects-only PDF and replace the user's projects_pdf-sourced projects.

    The whole document is treated as a projects list (no section heading required).
    Only the projects table is touched; CV-sourced projects are left untouched.
    """
    text = pdf.extract_text(data)
    projects = project_extract.extract_projects(text, section_only=False)

    try:
        await replace_projects(db, user_id, projects, ProjectSource.PROJECTS_PDF)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await _list_projects(db, user_id, ProjectSource.PROJECTS_PDF)
