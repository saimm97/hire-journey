"""Fetch each configured company from exactly one allowlisted ATS adapter.

Ingestion is deliberately user-independent: every valid public posting is
returned for persistence. Profile title/location filters belong to the later
recommendation query and must never discard inventory here.
"""

import asyncio
import logging
from dataclasses import dataclass, field

from app.models.company import Company
from app.sources import source_for_feed_url
from app.sources.base import RawJob

logger = logging.getLogger(__name__)

CONCURRENCY = 12
PROVIDER_CONCURRENCY = {
    "greenhouse": 6,
    "lever": 4,
    "ashby": 4,
}


@dataclass
class CompanyFetchResult:
    company_id: int
    provider: str | None = None
    jobs: list[RawJob] = field(default_factory=list)
    error_code: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error_code is None


async def _fetch_one(
    company: Company,
    global_sem: asyncio.Semaphore,
    provider_sems: dict[str, asyncio.Semaphore],
) -> CompanyFetchResult:
    # Keep only primitive company metadata in results. A later database
    # rollback expires every ORM object loaded by the session, and touching an
    # expired Company from this asynchronous persistence loop can trigger an
    # implicit database read (and MissingGreenlet) while handling an error.
    company_id = company.id
    feed_url = company.careers_url
    if not feed_url:
        return CompanyFetchResult(company_id=company_id, error_code="missing_feed_url")

    source = source_for_feed_url(feed_url)
    if source is None:
        logger.warning("Unsupported ATS feed URL for company_id=%s", company_id)
        return CompanyFetchResult(company_id=company_id, error_code="unsupported_feed_url")

    try:
        async with global_sem, provider_sems[source.name]:
            fetched = await source.fetch_url(feed_url, company.name)
    except Exception as exc:
        # Source failures are isolated: never abort other company scans and do
        # not put response bodies or job content in logs.
        logger.warning(
            "ATS fetch failed provider=%s company_id=%s error_type=%s",
            source.name,
            company_id,
            type(exc).__name__,
        )
        return CompanyFetchResult(
            company_id=company_id,
            provider=source.name,
            error_code="fetch_failed",
        )

    # A provider occasionally returns the same posting more than once (for
    # example through multiple departments). Collapse it before DB work while
    # retaining response order.
    jobs_by_url: dict[str, RawJob] = {}
    for job in fetched:
        if job.url and job.url not in jobs_by_url:
            jobs_by_url[job.url] = job

    jobs = list(jobs_by_url.values())
    logger.info(
        "ATS fetch succeeded provider=%s company_id=%s jobs=%d",
        source.name,
        company_id,
        len(jobs),
    )
    return CompanyFetchResult(company_id=company_id, provider=source.name, jobs=jobs)


async def fetch_all(companies: list[Company]) -> list[CompanyFetchResult]:
    """Fetch all company feeds with global and provider-specific limits."""
    global_sem = asyncio.Semaphore(CONCURRENCY)
    provider_sems = {
        provider: asyncio.Semaphore(limit) for provider, limit in PROVIDER_CONCURRENCY.items()
    }
    tasks = [_fetch_one(company, global_sem, provider_sems) for company in companies]
    return list(await asyncio.gather(*tasks))
