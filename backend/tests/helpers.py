"""Row-seeding helpers for profile-endpoint tests, each committing in its own session."""

import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.candidate import Candidate
from app.models.project import Project, ProjectSource
from app.models.resume import Resume


async def seed_candidate(user_id: uuid.UUID, **fields: object) -> None:
    """Insert a candidate row for the user."""
    async with AsyncSessionLocal() as session:
        session.add(Candidate(user_id=user_id, **fields))
        await session.commit()


async def seed_resume(
    user_id: uuid.UUID, *, summary: str | None = None, is_active: bool = True
) -> None:
    """Insert a resume whose parsed content carries the given summary."""
    async with AsyncSessionLocal() as session:
        session.add(
            Resume(
                user_id=user_id,
                file_name="cv.pdf",
                parsed_content={"summary": summary},
                is_active=is_active,
            )
        )
        await session.commit()


async def seed_project(
    user_id: uuid.UUID, *, name: str, source: str = ProjectSource.CV, **fields: object
) -> None:
    """Insert a project row for the user."""
    async with AsyncSessionLocal() as session:
        session.add(Project(user_id=user_id, name=name, source=source, **fields))
        await session.commit()


async def load_candidate(user_id: uuid.UUID) -> Candidate:
    """Read the candidate back through a fresh session."""
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(select(Candidate).where(Candidate.user_id == user_id))
        ).scalar_one()


async def load_cv_projects(user_id: uuid.UUID) -> list[Project]:
    """Read the user's CV-sourced projects, oldest first, through a fresh session."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.source == ProjectSource.CV)
            .order_by(Project.created_at)
        )
        return list(result.scalars().all())
