"""Idempotently persist normalized ATS postings using the existing URL key."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.sources import SOURCES, source_for_url
from app.sources.base import RawJob
from app.sources.html_sanitizer import sanitize_job_html

UPSERT_CHUNK_SIZE = 500
MAX_JOB_TITLE_LENGTH = 500
MAX_JOB_LOCATION_LENGTH = 255


def _bounded_text(value: str | None, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned[:max_length] or None


def _values_for_job(raw: RawJob, company_id: int) -> dict | None:
    title = _bounded_text(raw.title, MAX_JOB_TITLE_LENGTH)
    url = raw.url.strip() if isinstance(raw.url, str) else ""
    if title is None or not url:
        return None
    description = sanitize_job_html(raw.description)
    return {
        "company_id": company_id,
        "title": title,
        "url": url,
        "location": _bounded_text(raw.location, MAX_JOB_LOCATION_LENGTH),
        "description": description or None,
        "posted_at": raw.posted_at,
        "deadline": raw.deadline,
        "salary_min": raw.salary_min,
        "salary_max": raw.salary_max,
    }


async def upsert_job(db: AsyncSession, raw: RawJob, company_id: int) -> Job | None:
    """Insert or refresh one job, returning its canonical URL-keyed row."""
    values = _values_for_job(raw, company_id)
    if values is None:
        return None

    stmt = pg_insert(Job).values(values)
    cols = Job.__table__.c
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=["url"],
        set_={
            "title": excluded.title,
            "description": func.coalesce(excluded.description, cols.description),
            "location": func.coalesce(excluded.location, cols.location),
            "posted_at": func.coalesce(excluded.posted_at, cols.posted_at),
            "deadline": func.coalesce(excluded.deadline, cols.deadline),
            # Compensation is an authoritative successful-snapshot field.
            # Replacing with NULL lets employer removals and parser corrections
            # clear stale values; failed provider fetches never reach upsert.
            "salary_min": excluded.salary_min,
            "salary_max": excluded.salary_max,
            "updated_at": func.now(),
        },
    ).returning(Job)
    stmt = stmt.execution_options(populate_existing=True)
    result = await db.execute(stmt)
    return result.scalar_one()


async def ensure_description(db: AsyncSession, job: Job) -> None:
    """Populate job.description from its board's per-job API if it is NULL.

    The posting URL identifies which adapter to ask. Adapters whose list API
    already returns descriptions answer None, so a job stored without one is
    normally from a board (like Greenhouse) that needs the extra call.
    """
    if job.description:
        return
    if not job.company.slug:
        return

    source = source_for_url(job.url)
    # Unrecognised host (e.g. a custom ATS domain): ask every adapter and take
    # the first that can resolve it.
    candidates = [source] if source else list(SOURCES.values())

    for candidate in candidates:
        desc = await candidate.fetch_description(job.company.slug, job.url)
        if desc:
            job.description = sanitize_job_html(desc)
            await db.flush()
            return


async def get_job_with_description(db: AsyncSession, job_id: int) -> Job | None:
    """Load a job (with company) and lazily backfill its description."""
    job = (
        await db.execute(select(Job).where(Job.id == job_id).options(selectinload(Job.company)))
    ).scalar_one_or_none()

    if job is not None:
        await ensure_description(db, job)

    return job


async def upsert_jobs(db: AsyncSession, raw_jobs: list[RawJob], company_id: int) -> list[Job]:
    """Bulk-upsert a company snapshot and return the canonical rows.

    Duplicate or blank URLs are removed before issuing SQL. Chunking keeps the
    PostgreSQL bind-parameter count bounded for unusually large boards.
    """
    unique_jobs: dict[str, dict] = {}
    for raw in raw_jobs:
        values = _values_for_job(raw, company_id)
        if values is not None and values["url"] not in unique_jobs:
            unique_jobs[values["url"]] = values

    raw_values = list(unique_jobs.values())
    jobs: list[Job] = []
    for offset in range(0, len(raw_values), UPSERT_CHUNK_SIZE):
        chunk = raw_values[offset : offset + UPSERT_CHUNK_SIZE]
        stmt = pg_insert(Job).values(chunk)
        cols = Job.__table__.c
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=["url"],
            set_={
                "title": excluded.title,
                "description": func.coalesce(excluded.description, cols.description),
                "location": func.coalesce(excluded.location, cols.location),
                "posted_at": func.coalesce(excluded.posted_at, cols.posted_at),
                "deadline": func.coalesce(excluded.deadline, cols.deadline),
                # See upsert_job: salary intentionally replaces rather than
                # coalesces because this is a successful board snapshot.
                "salary_min": excluded.salary_min,
                "salary_max": excluded.salary_max,
                "updated_at": func.now(),
            },
        ).returning(Job)
        stmt = stmt.execution_options(populate_existing=True)
        result = await db.execute(stmt)
        jobs.extend(result.scalars().all())
    return jobs
