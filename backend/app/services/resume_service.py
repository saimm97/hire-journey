"""Concurrency-safe resume creation and replacement."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.models.user import User

MAX_RESUMES_PER_USER = 2


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
    """Add a resume without committing, enforcing the per-user limit.

    The newest resume (by created_at) is the one the app uses.
    """
    await _lock_user(db, user_id)
    existing = await db.scalar(
        select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
    )
    if existing >= MAX_RESUMES_PER_USER:
        raise ResumeLimitError(
            f"This account already has {MAX_RESUMES_PER_USER} resumes; "
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
