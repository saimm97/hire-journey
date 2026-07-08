"""The scheduled job pipeline — the work the background timer runs.

Step A (collect): fetch jobs from every active ATS board and upsert them into the
`jobs` table (URL-deduped, so re-runs don't create duplicates).

Step A.5 (enrich): Greenhouse's list API omits job descriptions, so after collecting
we backfill the missing ones from Greenhouse's per-job endpoint. Descriptions persist
once stored, so this only costs requests for *newly seen* Greenhouse jobs after the
first (cold-start) run.

Step B (per-user scoring) will be added here next.

Runs as a background task with no web request, so it opens its own DB session via
AsyncSessionLocal rather than the request-scoped `get_db` dependency.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.job import Job
from app.models.source import Source
from app.services import company_service, fetch_service, job_service
from app.sources.greenhouse import GreenhouseSource

logger = logging.getLogger(__name__)

# How many Greenhouse detail requests to run at once. Kept modest to stay polite to
# Greenhouse's API — a background job has no user waiting on it.
ENRICH_CONCURRENCY = 8


async def _collect(db) -> tuple[int, int]:
    """Step A: fetch + upsert jobs from all active boards. Returns (jobs, companies)."""
    companies = await company_service.get_active_companies(db)
    fetch_results = await fetch_service.fetch_all(companies)

    jobs_collected = 0
    for company, raw_jobs in fetch_results:
        if not raw_jobs:
            continue
        saved = await job_service.upsert_jobs(db, raw_jobs, company)
        jobs_collected += len(saved)

    await db.commit()
    return jobs_collected, len(companies)


async def _enrich_descriptions(db) -> int:
    """Step A.5: backfill descriptions for Greenhouse jobs missing them.

    Only the HTTP fetches run concurrently; the DB writes are plain in-memory
    attribute assignments on already-loaded rows, committed once at the end — so the
    single AsyncSession is never touched by two tasks at once.
    """
    jobs = (
        await db.execute(
            select(Job)
            .join(Source, Job.source_id == Source.source_id)
            .where(Source.name == "greenhouse", Job.description.is_(None))
            .options(selectinload(Job.company))
        )
    ).scalars().all()

    if not jobs:
        return 0

    sem = asyncio.Semaphore(ENRICH_CONCURRENCY)

    async def fetch_one(job: Job) -> int:
        async with sem:
            desc = await GreenhouseSource.fetch_description(job.company.slug, job.url)
        if desc:
            job.description = desc
            return 1
        return 0

    filled = sum(await asyncio.gather(*(fetch_one(j) for j in jobs)))
    await db.commit()
    return filled


async def run_pipeline() -> dict:
    """Run one full pipeline pass. Returns a small summary for logging/tests."""
    async with AsyncSessionLocal() as db:
        jobs_collected, n_companies = await _collect(db)
        enriched = await _enrich_descriptions(db)

    summary = {
        "companies": n_companies,
        "jobs_collected": jobs_collected,
        "descriptions_enriched": enriched,
    }
    logger.info(
        "pipeline: %d jobs across %d companies, %d Greenhouse descriptions enriched",
        jobs_collected,
        n_companies,
        enriched,
    )
    return summary
