"""Job-scan orchestration and on-the-fly result scoring.

run_scan() fetches jobs from every scannable company (all ATS adapters are
tried per company) and upserts them into the jobs table.

get_results() is the read path: it keyword-scores the stored jobs against the
caller's search terms plus the skills from their most recent resume, entirely
in memory — no scores are persisted.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.schemas.search import JobResult, SearchResultsResponse
from app.services import company_service, fetch_service, job_service, resume_service, score_service


async def run_scan(db: AsyncSession) -> int:
    """Fetch, filter, and upsert jobs from all scannable companies. Returns the count."""
    companies = await company_service.get_scannable_companies(db)
    fetch_results = await fetch_service.fetch_all(companies)

    total = 0
    for company, raw_jobs in fetch_results:
        if not raw_jobs:
            continue
        jobs = await job_service.upsert_jobs(db, raw_jobs, company)
        total += len(jobs)

    await db.commit()
    return total


async def get_results(
    db: AsyncSession,
    user_id: int,
    search_terms: list[str],
    min_score: int = 0,
    limit: int = 20,
    offset: int = 0,
) -> SearchResultsResponse:
    """Score all stored jobs against the terms + the user's resume skills, ranked."""
    resume = await resume_service.latest_resume(db, user_id)
    resume_skills: list[str] = []
    if resume and resume.parsed_content:
        resume_skills = [s for s in resume.parsed_content.get("skills", []) if isinstance(s, str)]

    jobs = (await db.execute(select(Job).options(selectinload(Job.company)))).scalars().all()

    scored = [
        (
            score_service.keyword_score(
                title=job.title,
                description=job.description or "",
                search_terms=search_terms,
                resume_skills=resume_skills,
            ),
            job,
        )
        for job in jobs
    ]
    ranked = sorted(
        ((score, job) for score, job in scored if score >= min_score),
        key=lambda pair: pair[0],
        reverse=True,
    )

    page = ranked[offset : offset + limit]
    return SearchResultsResponse(
        total=len(ranked),
        results=[
            JobResult(
                job_id=job.id,
                title=job.title,
                company_name=job.company.name,
                location=job.location,
                url=job.url,
                score=score,
            )
            for score, job in page
        ],
    )
