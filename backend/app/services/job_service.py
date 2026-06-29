"""Persist raw fetched jobs to the database.

Handles the primary dedup: the jobs table has a unique constraint on url, so we
use INSERT ... ON CONFLICT DO NOTHING and then SELECT to get the canonical row
(whether we inserted it now or it already existed from a previous scan).

This means the jobs table grows incrementally across scans — a job fetched today
that was already stored last week is not re-inserted, just re-scored for this
session.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.job import Job
from app.sources.base import RawJob


async def upsert_job(db: AsyncSession, raw: RawJob, company: Company) -> Job | None:
    """Insert the job if its URL is new, then return the canonical DB row.

    Returns None if the raw job has no URL (malformed ATS response).
    """
    if not raw.url:
        return None

    new_desc = raw.description or None
    stmt = pg_insert(Job).values(
        job_id=uuid.uuid4(),
        source_id=company.source_id,
        company_id=company.company_id,
        title=raw.title,
        url=raw.url,
        location=raw.location or None,
        description=new_desc,
    )
    # If the job already exists (same URL), backfill description if it was NULL.
    # All other fields are intentionally left unchanged — title and location come
    # from the same API and won't drift meaningfully between scans.
    stmt = stmt.on_conflict_do_update(
        index_elements=["url"],
        set_={"description": new_desc},
        where=Job.__table__.c.description.is_(None),
    )
    await db.execute(stmt)

    result = await db.execute(select(Job).where(Job.url == raw.url))
    return result.scalar_one_or_none()


async def ensure_description(db: AsyncSession, job: Job) -> None:
    """Populate job.description from the Greenhouse per-job API if it is NULL.

    Only fires for Greenhouse jobs — Ashby and Lever return descriptions in the
    list endpoint so those are already populated after a scan.
    """
    if job.description:
        return
    if job.source.name != "greenhouse":
        return

    from app.sources.greenhouse import GreenhouseSource  # avoid circular at module level

    desc = await GreenhouseSource.fetch_description(job.company.slug, job.url)
    if desc:
        job.description = desc
        await db.flush()


async def get_job_with_description(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    """Load a job (with source + company) and lazily backfill its description."""
    job = (
        await db.execute(
            select(Job)
            .where(Job.job_id == job_id)
            .options(selectinload(Job.source), selectinload(Job.company))
        )
    ).scalar_one_or_none()

    if job is not None:
        await ensure_description(db, job)

    return job


async def upsert_jobs(
    db: AsyncSession, raw_jobs: list[RawJob], company: Company
) -> list[Job]:
    """Upsert a batch of raw jobs for one company. Returns the canonical DB rows."""
    jobs = []
    for raw in raw_jobs:
        job = await upsert_job(db, raw, company)
        if job is not None:
            jobs.append(job)
    return jobs
