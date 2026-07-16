"""Search orchestration: the four-stage pipeline in one place.

Stage 1 — Create session
Stage 2 — Fetch + filter jobs from all active companies (parallel)
Stage 3 — Upsert jobs to DB (dedup at DB level)
Stage 4 — Keyword score each job, store in job_scores

get_results() is the read path: returns scored jobs for a session, ranked by
score descending, with pagination.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.job_score import JobScore
from app.models.resume import Resume
from app.models.search_session import SearchSession
from app.schemas.search import JobResult, SearchResultsResponse
from app.services import company_service, fetch_service, job_service, score_service


async def run_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    search_terms: list[str],
) -> tuple[SearchSession, int]:
    """Run the full pipeline. Returns the created session and total jobs scored."""

    resume_row = (
        await db.execute(
            select(Resume).where(
                Resume.resume_id == resume_id,
                Resume.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if resume_row is None:
        raise ValueError(f"Resume {resume_id} not found")

    # Stage 1: session
    session = SearchSession(
        user_id=user_id,
        resume_id=resume_id,
        search_terms=search_terms,
    )
    db.add(session)
    await db.flush()  # get session_id without committing

    # Stage 2: fetch + filter
    companies = await company_service.get_active_companies(db)
    fetch_results = await fetch_service.fetch_all(companies)

    # Load resume skills for scoring (may be empty if resume isn't parsed yet)
    resume_skills: list[str] = []
    if resume_row and resume_row.parsed_content:
        resume_skills = [
            s.get("name", "") for s in resume_row.parsed_content.get("skills", []) if s.get("name")
        ]

    # Stages 3 + 4: upsert jobs → score → store job_scores
    total_scored = 0
    for company, raw_jobs in fetch_results:
        if not raw_jobs:
            continue

        jobs = await job_service.upsert_jobs(db, raw_jobs, company)

        for job in jobs:
            s = score_service.keyword_score(
                title=job.title,
                description=job.description or "",
                search_terms=search_terms,
                resume_skills=resume_skills,
            )
            db.add(
                JobScore(
                    job_id=job.job_id,
                    session_id=session.session_id,
                    user_id=user_id,
                    resume_id=resume_id,
                    score=s,
                )
            )
            total_scored += 1

    await db.commit()
    await db.refresh(session)
    return session, total_scored


async def get_results(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    min_score: int = 0,
    limit: int = 20,
    offset: int = 0,
) -> SearchResultsResponse:
    """Return ranked job results for a session, filtered by minimum score."""

    # Count total matching
    count_q = (
        select(func.count())
        .select_from(JobScore)
        .where(
            JobScore.session_id == session_id,
            JobScore.user_id == user_id,
            JobScore.score >= min_score,
        )
    )
    total = (await db.execute(count_q)).scalar_one()

    # Fetch page
    rows_q = (
        select(JobScore)
        .where(
            JobScore.session_id == session_id,
            JobScore.user_id == user_id,
            JobScore.score >= min_score,
        )
        .options(selectinload(JobScore.job).selectinload(Job.company))
        .order_by(JobScore.score.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(rows_q)).scalars().all()

    results = [
        JobResult(
            job_id=row.job.job_id,
            title=row.job.title,
            company_name=row.job.company.name,
            location=row.job.location,
            url=row.job.url,
            score=row.score,
        )
        for row in rows
    ]

    return SearchResultsResponse(
        session_id=session_id,
        total=total,
        results=results,
    )
