"""Orchestrates the LLM deep evaluation pipeline.

Flow:
  1. Load job from DB — fetch Greenhouse description lazily if NULL
  2. Load resume from DB
  3. Call the LangChain evaluator agent
  4. Persist Evaluation record and return it
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluator import evaluate_job
from app.models.evaluation import Evaluation
from app.models.resume import Resume
from app.services.job_service import get_job_with_description


async def run_evaluation(
    db: AsyncSession,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    resume_id: uuid.UUID,
) -> Evaluation:
    """Run LLM evaluation for (user, job, resume). Stores and returns the result.

    If an evaluation for this (job, user, resume) triple already exists it is
    returned without re-running the LLM.
    """
    existing = (
        await db.execute(
            select(Evaluation).where(
                Evaluation.job_id == job_id,
                Evaluation.user_id == user_id,
                Evaluation.resume_id == resume_id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    job = await get_job_with_description(db, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    resume = (
        await db.execute(
            select(Resume).where(
                Resume.resume_id == resume_id,
                Resume.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if resume is None:
        raise ValueError(f"Resume {resume_id} not found")

    skills: list[str] = []
    if resume.parsed_content:
        skills = [
            s.get("name", "") for s in resume.parsed_content.get("skills", []) if s.get("name")
        ]

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
        user_id=user_id,
        resume_id=resume_id,
        match_score=result.match_score,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        recommendations=result.recommendations,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation
