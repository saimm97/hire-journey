"""Parallel ATS job fetching with concurrency cap and per-company filtering.

Companies no longer record which ATS they use — every adapter is tried for each
company's slug and the results are combined (a slug that doesn't exist on a
board simply yields nothing). Fetches run concurrently (capped at CONCURRENCY
simultaneous requests) and title/location filters from companies.yaml apply.

A failed fetch for one company/adapter is logged and skipped — it never aborts
the whole scan.
"""

import asyncio
import logging
from pathlib import Path

import yaml

from app.models.company import Company
from app.services.filter_service import apply_filters
from app.sources import SOURCES
from app.sources.base import RawJob

logger = logging.getLogger(__name__)

CONCURRENCY = 10
_YAML_PATH = Path(__file__).parent.parent.parent / "config" / "companies.yaml"


def _load_filters() -> dict:
    with open(_YAML_PATH) as f:
        config = yaml.safe_load(f)
    return {
        "positive": config.get("title_filter", {}).get("positive", []),
        "negative": config.get("title_filter", {}).get("negative", []),
        "allow": config.get("location_filter", {}).get("allow", []),
        "block": config.get("location_filter", {}).get("block", []),
    }


async def _fetch_one(
    company: Company,
    filters: dict,
    sem: asyncio.Semaphore,
) -> tuple[Company, list[RawJob]]:
    if not company.slug:
        return company, []

    raw_jobs: list[RawJob] = []
    seen_urls: set[str] = set()
    async with sem:
        for source_name, source in SOURCES.items():
            try:
                fetched = await source.fetch(company.slug, company.name)
            except Exception as exc:
                logger.debug("%s fetch failed for %s: %s", source_name, company.name, exc)
                continue
            for job in fetched:
                if job.url and job.url in seen_urls:
                    continue
                seen_urls.add(job.url)
                raw_jobs.append(job)

    filtered = apply_filters(
        raw_jobs,
        filters["positive"],
        filters["negative"],
        filters["allow"],
        filters["block"],
    )
    logger.debug("%s: %d fetched, %d after filter", company.name, len(raw_jobs), len(filtered))
    return company, filtered


async def fetch_all(companies: list[Company]) -> list[tuple[Company, list[RawJob]]]:
    """Fetch and filter jobs for all companies. Returns (company, jobs) pairs."""
    filters = _load_filters()
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [_fetch_one(c, filters, sem) for c in companies]
    results = await asyncio.gather(*tasks)
    return list(results)
