"""Concurrency-safe resume creation and replacement."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.resume import Resume
from app.models.user import User

logger = logging.getLogger(__name__)


class ResumeLimitError(ValueError):
    """Raised when the account already holds the maximum number of resumes."""


class ResumeNotFoundError(ValueError):
    """Raised when a resume does not belong to the current user."""


async def _lock_user(db: AsyncSession, user_id: int) -> None:
    """Serialize resume mutations for one user so the count-based limit is race-safe."""
    locked_user_id = await db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    if locked_user_id is None:
        raise ResumeNotFoundError("User does not exist")


async def create_resume(
    db: AsyncSession,
    *,
    user_id: int,
    file_name: str,
    raw_content: str | None,
    parsed_content: dict | None,
) -> Resume:
    """Add or reuse a resume without committing, enforcing the per-user limit.

    Exact same-content retries are idempotent. The user lock makes the lookup +
    insert atomic, so two timed-out requests that finish concurrently cannot
    consume both resume slots with the same document.
    """
    await _lock_user(db, user_id)

    if raw_content:
        existing_resume = (
            await db.execute(
                select(Resume)
                .where(
                    Resume.user_id == user_id,
                    Resume.raw_content == raw_content,
                )
                .order_by(Resume.created_at.desc(), Resume.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing_resume is not None:
            # Keep the latest successful extraction while preserving identity.
            existing_resume.file_name = file_name
            existing_resume.raw_content = raw_content
            existing_resume.parsed_content = parsed_content
            await db.flush()
            logger.info(
                "Reused identical resume [user_id=%s resume_id=%s]",
                user_id,
                existing_resume.id,
            )
            return existing_resume

    existing = await db.scalar(
        select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
    )
    if existing >= settings.max_resumes_per_user:
        raise ResumeLimitError(
            f"This account already has {settings.max_resumes_per_user} resumes; "
            "replace or delete one before uploading."
        )

    resume = Resume(
        user_id=user_id,
        file_name=file_name,
        raw_content=raw_content,
        parsed_content=parsed_content,
    )
    db.add(resume)
    await db.flush()
    return resume


async def replace_resume(
    db: AsyncSession,
    *,
    user_id: int,
    resume_id: int,
    file_name: str,
    raw_content: str | None,
    parsed_content: dict | None,
) -> Resume:
    """Overwrite one owned resume without committing."""
    await _lock_user(db, user_id)
    resume = (
        await db.execute(
            select(Resume).where(
                Resume.id == resume_id,
                Resume.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if resume is None:
        raise ResumeNotFoundError("Resume not found")

    resume.file_name = file_name
    resume.raw_content = raw_content
    resume.parsed_content = parsed_content
    await db.flush()
    return resume


async def list_resumes(db: AsyncSession, user_id: int) -> list[Resume]:
    return list(
        (
            await db.scalars(
                select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
            )
        ).all()
    )


async def latest_resume(db: AsyncSession, user_id: int) -> Resume | None:
    """The user's most recent upload — the resume the app treats as current."""
    return (
        await db.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
