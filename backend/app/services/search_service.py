"""ATS ingestion orchestration and on-the-fly result scoring.

run_scan() fetches each configured careers URL through its one matching adapter
and commits every company independently.

get_results() is the read path: it keyword-scores the stored jobs against the
caller's search terms plus the skills from their most recent resume, entirely
in memory — no scores are persisted.
"""

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, engine
from app.models.job import Job
from app.schemas.search import JobResult, SearchResultsResponse
from app.services import company_service, fetch_service, job_service, profile_service, score_service

logger = logging.getLogger(__name__)
INGESTION_LOCK_ID = 684_731_902


class IngestionAlreadyRunningError(RuntimeError):
    pass


async def run_scan(db: AsyncSession) -> int:
    """Fetch and idempotently persist every supported company job feed.

    Fetch and persistence failures are isolated per company. A successful
    company snapshot is committed immediately, so a later failure cannot roll
    back already-ingested inventory.
    """
    companies = await company_service.get_scannable_companies(db)
    # Do not hold an idle database transaction open during network I/O.
    await db.commit()
    fetch_results = await fetch_service.fetch_all(companies)

    total = 0
    for fetch_result in fetch_results:
        if not fetch_result.succeeded:
            continue
        try:
            jobs = await job_service.upsert_jobs(
                db,
                fetch_result.jobs,
                fetch_result.company_id,
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            # Do not emit the SQLAlchemy traceback here: DBAPI errors include
            # bound parameters, which can dump entire job descriptions into
            # scheduler logs. The company and exception type are sufficient
            # to identify and isolate the failed batch safely.
            logger.error(
                "ATS persistence failed company_id=%s error_type=%s",
                fetch_result.company_id,
                type(exc).__name__,
            )
            continue
        total += len(jobs)

    return total


async def run_scan_locked() -> int:
    """Run ingestion while holding one process-independent PostgreSQL lock."""
    async with engine.connect() as lock_connection:
        acquired = await lock_connection.scalar(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": INGESTION_LOCK_ID},
        )
        if not acquired:
            raise IngestionAlreadyRunningError("A job-ingestion run is already active")

        try:
            async with AsyncSessionLocal() as db:
                return await run_scan(db)
        finally:
            await lock_connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": INGESTION_LOCK_ID},
            )


async def get_results(
    db: AsyncSession,
    user_id: int,
    search_terms: list[str] | None = None,
    min_score: int = 0,
    limit: int = 20,
    offset: int = 0,
) -> SearchResultsResponse:
    """Rank stored jobs for this user, scored entirely in memory.

    Terms default to the user's ``desired_roles`` (the profile is the query);
    an explicit ``search_terms`` overrides them, e.g. a search box. The user's
    technologies are the scoring bonus. No profile / no terms → empty feed.
    """
    roles, technologies = await profile_service.get_match_preferences(db, user_id)
    terms = search_terms if search_terms else roles

    jobs = (await db.execute(select(Job).options(selectinload(Job.company)))).scalars().all()

    scored = [
        (
            score_service.keyword_score(
                title=job.title,
                description=job.description or "",
                search_terms=terms,
                resume_skills=technologies,
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
