"""Fetch each configured company from exactly one allowlisted ATS adapter.

Ingestion is deliberately user-independent: every valid public posting is
returned for persistence. Profile title/location filters belong to the later
recommendation query and must never discard inventory here.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from uuid import UUID

import httpx

from app.config import settings
from app.models.company import Company
from app.services.ingestion_report import (
    IngestionIssue,
    IssueCode,
    IssueStage,
    sanitize_feed_url,
)
from app.sources import (
    SOURCE_REGISTRY,
    registration_for_feed_host,
    registration_for_feed_url,
)
from app.sources.base import (
    ATSInvalidFeedError,
    ATSInvalidJSONError,
    ATSResponseTooLargeError,
    RawJob,
)

logger = logging.getLogger(__name__)


@dataclass
class CompanyFetchResult:
    company_id: int
    provider: str | None = None
    feed_url: str | None = None
    jobs: list[RawJob] = field(default_factory=list)
    error: IngestionIssue | None = None

    @property
    def error_code(self) -> str | None:
        return self.error.code.value if self.error is not None else None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def _fetch_issue(
    *,
    company_id: int,
    company_name: str,
    provider: str,
    feed_url: str | None,
    exc: Exception,
) -> IngestionIssue:
    http_status = None
    retry_eligible = False
    stage = IssueStage.FETCH
    if isinstance(exc, ATSResponseTooLargeError):
        code = IssueCode.RESPONSE_TOO_LARGE
        message = "The provider response exceeded the configured size limit."
    elif isinstance(exc, ATSInvalidJSONError):
        code = IssueCode.INVALID_JSON
        stage = IssueStage.PARSE
        message = "The provider response was not valid JSON."
    elif isinstance(exc, ATSInvalidFeedError):
        code = IssueCode.INVALID_FEED
        stage = IssueStage.PARSE
        message = "The provider response did not contain a valid job feed."
    elif isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        code = IssueCode.REQUEST_TIMEOUT
        message = "The provider request timed out."
        retry_eligible = True
    elif isinstance(exc, httpx.HTTPStatusError):
        http_status = exc.response.status_code
        if http_status == 429:
            code = IssueCode.RATE_LIMITED
            message = "The provider rate limit was exhausted after retries."
            retry_eligible = True
        else:
            code = IssueCode.PROVIDER_HTTP_ERROR
            message = f"The provider feed returned HTTP {http_status}."
            retry_eligible = http_status in {500, 502, 503, 504}
    elif isinstance(exc, httpx.TransportError):
        code = IssueCode.CONNECTION_FAILED
        message = "The provider connection failed."
        retry_eligible = True
    else:
        code = IssueCode.UNEXPECTED_FETCH_ERROR
        message = "The provider feed could not be fetched."

    return IngestionIssue(
        company_id=company_id,
        company_name=company_name,
        provider=provider,
        feed_url=feed_url,
        stage=stage,
        code=code,
        message=message,
        exception_type=type(exc).__name__,
        http_status=http_status,
        retry_eligible=retry_eligible,
    )


async def _fetch_one(
    company: Company,
    global_sem: asyncio.Semaphore,
    provider_sems: dict[str, asyncio.Semaphore],
    run_id: UUID | None = None,
) -> CompanyFetchResult:
    # Keep only primitive company metadata in results. A later database
    # rollback expires every ORM object loaded by the session, and touching an
    # expired Company from this asynchronous persistence loop can trigger an
    # implicit database read (and MissingGreenlet) while handling an error.
    company_id = company.id
    company_name = company.name
    feed_url = company.careers_url
    safe_feed_url = sanitize_feed_url(feed_url)
    if not feed_url:
        return CompanyFetchResult(
            company_id=company_id,
            feed_url=safe_feed_url,
            error=IngestionIssue(
                company_id=company_id,
                company_name=company_name,
                feed_url=safe_feed_url,
                stage=IssueStage.ROUTING,
                code=IssueCode.INVALID_FEED_URL,
                message="The configured feed URL is invalid or unsupported.",
            ),
        )

    registration = registration_for_feed_url(feed_url)
    if registration is None:
        diagnostic_registration = registration_for_feed_host(feed_url)
        provider = (
            diagnostic_registration.source.name if diagnostic_registration is not None else None
        )
        logger.warning(
            "ATS feed rejected run_id=%s provider=%s company_id=%s code=%s feed_url=%s",
            run_id,
            provider,
            company_id,
            IssueCode.INVALID_FEED_URL,
            safe_feed_url,
        )
        return CompanyFetchResult(
            company_id=company_id,
            provider=provider,
            feed_url=safe_feed_url,
            error=IngestionIssue(
                company_id=company_id,
                company_name=company_name,
                provider=provider,
                feed_url=safe_feed_url,
                stage=IssueStage.ROUTING,
                code=IssueCode.INVALID_FEED_URL,
                message="The configured feed URL is invalid or unsupported.",
            ),
        )

    source = registration.source
    # Both objects come from the validated source registry.
    provider_sem = provider_sems[source.name]
    try:
        # Provider-first avoids consuming a global slot while a saturated
        # provider queue waits. A running fetch intentionally retains both
        # permits through retry backoff to keep degraded providers bounded.
        async with provider_sem:
            async with global_sem:
                fetched = await source.fetch_url(feed_url, company.name)
    except Exception as exc:
        # Source failures are isolated: never abort other company scans and do
        # not put response bodies or job content in logs.
        issue = _fetch_issue(
            company_id=company_id,
            company_name=company_name,
            provider=source.name,
            feed_url=safe_feed_url,
            exc=exc,
        )
        logger.warning(
            "ATS fetch failed run_id=%s provider=%s company_id=%s code=%s "
            "error_type=%s feed_url=%s",
            run_id,
            source.name,
            company_id,
            issue.code,
            type(exc).__name__,
            safe_feed_url,
        )
        return CompanyFetchResult(
            company_id=company_id,
            provider=source.name,
            feed_url=safe_feed_url,
            error=issue,
        )

    # A provider occasionally returns the same posting more than once (for
    # example through multiple departments). Collapse it before DB work while
    # retaining response order.
    jobs_by_url: dict[str, RawJob] = {}
    for job in fetched:
        if job.url and job.url not in jobs_by_url:
            jobs_by_url[job.url] = job

    jobs = list(jobs_by_url.values())
    logger.debug(
        "ATS fetch succeeded run_id=%s provider=%s company_id=%s jobs=%d",
        run_id,
        source.name,
        company_id,
        len(jobs),
    )
    return CompanyFetchResult(
        company_id=company_id,
        provider=source.name,
        feed_url=safe_feed_url,
        jobs=jobs,
    )


async def fetch_all(
    companies: list[Company],
    *,
    run_id: UUID | None = None,
) -> list[CompanyFetchResult]:
    """Fetch all company feeds with global and provider-specific limits."""
    global_sem = asyncio.Semaphore(settings.ats_global_concurrency)
    provider_sems = {
        name: asyncio.Semaphore(registration.concurrency_limit)
        for name, registration in SOURCE_REGISTRY.items()
    }
    tasks = [_fetch_one(company, global_sem, provider_sems, run_id=run_id) for company in companies]
    return list(await asyncio.gather(*tasks))
