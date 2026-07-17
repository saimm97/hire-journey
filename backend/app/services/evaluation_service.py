"""Orchestrates the LLM deep evaluation pipeline.

Flow:
  1. Load the caller's profile and most recent resume
  2. Load job from DB — fetch Greenhouse description lazily if NULL
  3. Call the LangChain evaluator agent
  4. Persist Evaluation record (keyed to the profile) and return it
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.evaluator import evaluate_job
from app.models.evaluation import Evaluation
from app.models.profile import Profile
from app.models.technology import ProfileTechnology
from app.services import resume_service
from app.services.job_service import get_job_with_description


async def run_evaluation(db: AsyncSession, user_id: int, job_id: int) -> Evaluation:
    """Run LLM evaluation of the user's profile against a job.

    If an evaluation for this (job, profile) pair already exists it is returned
    without re-running the LLM.
    """
    profile = (
        await db.execute(
            select(Profile)
            .where(Profile.user_id == user_id)
            .options(selectinload(Profile.technologies).selectinload(ProfileTechnology.technology))
        )
    ).scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile has not been created yet")

    existing = (
        await db.execute(
            select(Evaluation).where(
                Evaluation.job_id == job_id,
                Evaluation.profile_id == profile.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    job = await get_job_with_description(db, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    resume = await resume_service.latest_resume(db, user_id)
    if resume is None:
        raise ValueError("No resume uploaded yet")

    skills = [link.technology.name for link in profile.technologies]

    result = await evaluate_job(
        resume_text=resume.raw_content or "",
        skills=skills,
        job_title=job.title,
        company=job.company.name,
        location=job.location,
        description=job.description or "",
    )

    evaluation = Evaluation(
        job_id=job_id,
        profile_id=profile.id,
        match_score=result.match_score,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        recommendations=result.recommendations,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation
