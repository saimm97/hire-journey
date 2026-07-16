"""Concurrency-safe resume slot allocation and activation."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.models.user import User


class ResumeLimitError(ValueError):
    """Raised when both resume slots are already occupied."""


class ResumeNotFoundError(ValueError):
    """Raised when a resume does not belong to the current user."""


async def _lock_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Serialize resume mutations for one user to make slot allocation race-safe."""
    locked_user_id = await db.scalar(
        select(User.user_id).where(User.user_id == user_id).with_for_update()
    )
    if locked_user_id is None:
        raise ResumeNotFoundError("User does not exist")


async def create_resume(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    file_name: str,
    raw_content: str | None,
    parsed_content: dict | None,
    make_active: bool = True,
) -> Resume:
    """Allocate one of two slots and add a resume without committing."""
    await _lock_user(db, user_id)
    occupied_slots = set(
        (await db.scalars(select(Resume.slot_number).where(Resume.user_id == user_id))).all()
    )
    available_slots = sorted({1, 2} - occupied_slots)
    if not available_slots:
        raise ResumeLimitError(
            "This account already has two resumes; replace or delete one before uploading."
        )

    if make_active:
        await db.execute(
            update(Resume)
            .where(Resume.user_id == user_id, Resume.is_active.is_(True))
            .values(is_active=False)
        )

    resume = Resume(
        user_id=user_id,
        slot_number=available_slots[0],
        file_name=file_name,
        raw_content=raw_content,
        parsed_content=parsed_content,
        is_active=make_active or not occupied_slots,
    )
    db.add(resume)
    await db.flush()
    return resume


async def replace_resume(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    file_name: str,
    raw_content: str | None,
    parsed_content: dict | None,
) -> Resume:
    """Overwrite one owned slot and make that resume active without committing."""
    await _lock_user(db, user_id)
    resume = (
        await db.execute(
            select(Resume).where(
                Resume.resume_id == resume_id,
                Resume.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if resume is None:
        raise ResumeNotFoundError("Resume not found")

    await db.execute(
        update(Resume)
        .where(Resume.user_id == user_id, Resume.is_active.is_(True))
        .values(is_active=False)
    )
    resume.file_name = file_name
    resume.raw_content = raw_content
    resume.parsed_content = parsed_content
    resume.is_active = True
    await db.flush()
    return resume


async def list_resumes(db: AsyncSession, user_id: uuid.UUID) -> list[Resume]:
    return list(
        (
            await db.scalars(
                select(Resume).where(Resume.user_id == user_id).order_by(Resume.slot_number)
            )
        ).all()
    )


async def activate_resume(db: AsyncSession, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
    """Make one owned resume active and deactivate the other atomically."""
    try:
        await _lock_user(db, user_id)
        resume = (
            await db.execute(
                select(Resume).where(
                    Resume.resume_id == resume_id,
                    Resume.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if resume is None:
            raise ResumeNotFoundError("Resume not found")

        await db.execute(
            update(Resume)
            .where(Resume.user_id == user_id, Resume.is_active.is_(True))
            .values(is_active=False)
        )
        await db.execute(update(Resume).where(Resume.resume_id == resume_id).values(is_active=True))
        await db.commit()
        await db.refresh(resume)
        return resume
    except Exception:
        await db.rollback()
        raise
