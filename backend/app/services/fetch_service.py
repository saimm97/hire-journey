"""Parallel ATS job fetching with concurrency cap and per-company filtering.

Fetches all active companies concurrently (capped at CONCURRENCY simultaneous
requests), applies title and location filters from companies.yaml, and returns
a mapping of Company → filtered RawJob list.

A failed fetch for one company is logged and skipped — it never aborts the whole
scan. This mirrors career-ops behaviour where a single bad API response doesn't
stop the pipeline.
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
    source = SOURCES.get(company.source.name)
    if source is None:
        logger.warning("No adapter for source '%s' (company: %s)", company.source.name, company.name)
        return company, []

    async with sem:
        try:
            raw_jobs = await source.fetch(company.slug, company.name)
        except Exception as exc:
            logger.warning("Fetch failed for %s: %s", company.name, exc)
            return company, []

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
