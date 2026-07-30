"""ATS ingestion orchestration and on-the-fly result scoring.

run_scan() fetches each configured careers URL through its one matching adapter
and commits every company independently.

get_results() is the read path: it keyword-scores the stored jobs against the
caller's search terms plus the skills from their most recent resume, entirely
in memory — no scores are persisted.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, engine
from app.models.job import Job
from app.schemas.search import JobResult, SearchResultsResponse
from app.services import company_service, fetch_service, job_service, profile_service, score_service
from app.services.ingestion_report import (
    IngestionIssue,
    IngestionRunFailedError,
    IngestionRunReport,
    IssueCode,
    IssueStage,
    ProviderIngestionHealth,
    ProviderRunSummary,
    RunStatus,
)

logger = logging.getLogger(__name__)
INGESTION_LOCK_ID = 684_731_902


def _new_report() -> IngestionRunReport:
    started_at = datetime.now(timezone.utc)
    return IngestionRunReport(
        run_id=uuid4(),
        status=RunStatus.COMPLETED,
        started_at=started_at,
        finished_at=started_at,
        duration_ms=0,
    )


def _stamp_report(report: IngestionRunReport) -> None:
    finished_at = datetime.now(timezone.utc)
    report.finished_at = finished_at
    report.duration_ms = max(
        0,
        round((finished_at - report.started_at).total_seconds() * 1000),
    )


def _finish_report(
    report: IngestionRunReport,
    providers: dict[str, ProviderRunSummary],
) -> IngestionRunReport:
    _stamp_report(report)
    report.status = (
        RunStatus.COMPLETED_WITH_ERRORS if report.companies_failed else RunStatus.COMPLETED
    )
    for summary in providers.values():
        if summary.feeds_failed == summary.feeds_attempted:
            summary.ingestion_health = ProviderIngestionHealth.UNAVAILABLE
        elif summary.feeds_failed:
            summary.ingestion_health = ProviderIngestionHealth.DEGRADED
        elif summary.empty_feeds:
            summary.ingestion_health = ProviderIngestionHealth.WARNING
        else:
            summary.ingestion_health = ProviderIngestionHealth.HEALTHY
    report.providers = sorted(providers.values(), key=lambda item: item.provider)
    for summary in report.providers:
        logger.info(
            "ATS ingestion provider summary run_id=%s provider=%s ingestion_health=%s "
            "feeds_attempted=%d feeds_succeeded=%d feeds_failed=%d "
            "empty_feeds=%d persistence_failures=%d jobs_fetched=%d jobs_upserted=%d",
            report.run_id,
            summary.provider,
            summary.ingestion_health,
            summary.feeds_attempted,
            summary.feeds_succeeded,
            summary.feeds_failed,
            summary.empty_feeds,
            summary.persistence_failures,
            summary.jobs_fetched,
            summary.jobs_upserted,
        )
    logger.info(
        "ATS ingestion run completed run_id=%s status=%s duration_ms=%d "
        "companies_attempted=%d companies_succeeded=%d companies_failed=%d "
        "empty_feeds=%d jobs_fetched=%d jobs_upserted=%d warnings=%d errors=%d",
        report.run_id,
        report.status,
        report.duration_ms,
        report.companies_attempted,
        report.companies_succeeded,
        report.companies_failed,
        report.empty_feeds,
        report.jobs_fetched,
        report.jobs_upserted,
        len(report.warnings),
        len(report.errors),
    )
    return report


def _fail_report(report: IngestionRunReport, exc: Exception) -> IngestionRunReport:
    report.status = RunStatus.FAILED
    report.errors.append(
        IngestionIssue(
            stage=IssueStage.RUN,
            code=IssueCode.UNEXPECTED_RUN_ERROR,
            message="The ingestion run could not be completed.",
            exception_type=type(exc).__name__,
        )
    )
    _stamp_report(report)
    return report


async def run_scan(db: AsyncSession) -> IngestionRunReport:
    """Fetch and idempotently persist every supported company job feed.

    Fetch and persistence failures are isolated per company. A successful
    company snapshot is committed immediately, so a later failure cannot roll
    back already-ingested inventory.
    """
    report = _new_report()
    try:
        return await _execute_scan(db, report)
    except Exception as exc:
        try:
            await db.rollback()
        except Exception:
            pass
        _fail_report(report, exc)
        logger.exception(
            "ATS ingestion run failed run_id=%s error_type=%s",
            report.run_id,
            type(exc).__name__,
        )
        raise IngestionRunFailedError(report) from exc


async def _execute_scan(
    db: AsyncSession,
    report: IngestionRunReport,
) -> IngestionRunReport:
    companies = await company_service.get_scannable_companies(db)
    report.companies_attempted = len(companies)
    company_names = {company.id: company.name for company in companies}
    # Do not hold an idle database transaction open during network I/O.
    await db.commit()
    fetch_results = await fetch_service.fetch_all(companies, run_id=report.run_id)

    providers: dict[str, ProviderRunSummary] = {}
    for fetch_result in fetch_results:
        provider_summary = None
        if fetch_result.provider:
            provider_summary = providers.setdefault(
                fetch_result.provider,
                ProviderRunSummary(provider=fetch_result.provider),
            )
            provider_summary.feeds_attempted += 1
        if not fetch_result.succeeded:
            report.companies_failed += 1
            if fetch_result.error is not None:
                report.errors.append(fetch_result.error)
            if provider_summary is not None:
                provider_summary.feeds_failed += 1
            continue
        report.jobs_fetched += len(fetch_result.jobs)
        if provider_summary is not None:
            provider_summary.feeds_succeeded += 1
            provider_summary.jobs_fetched += len(fetch_result.jobs)
        if not fetch_result.jobs:
            warning = IngestionIssue(
                company_id=fetch_result.company_id,
                company_name=company_names.get(fetch_result.company_id),
                provider=fetch_result.provider,
                feed_url=fetch_result.feed_url,
                stage=IssueStage.FETCH,
                code=IssueCode.EMPTY_FEED,
                message="The provider returned a valid feed containing no jobs.",
            )
            report.warnings.append(warning)
            report.empty_feeds += 1
            if provider_summary is not None:
                provider_summary.empty_feeds += 1
            logger.warning(
                "ATS feed empty run_id=%s provider=%s company_id=%s code=%s feed_url=%s",
                report.run_id,
                fetch_result.provider,
                fetch_result.company_id,
                warning.code,
                fetch_result.feed_url,
            )
        try:
            jobs = await job_service.upsert_jobs(
                db,
                fetch_result.jobs,
                fetch_result.company_id,
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            issue = IngestionIssue(
                company_id=fetch_result.company_id,
                company_name=company_names.get(fetch_result.company_id),
                provider=fetch_result.provider,
                feed_url=fetch_result.feed_url,
                stage=IssueStage.PERSISTENCE,
                code=IssueCode.PERSISTENCE_FAILED,
                message="The fetched jobs could not be persisted.",
                exception_type=type(exc).__name__,
            )
            report.errors.append(issue)
            # Do not emit the SQLAlchemy traceback here: DBAPI errors include
            # bound parameters, which can dump entire job descriptions into
            # scheduler logs. The company and exception type are sufficient
            # to identify and isolate the failed batch safely.
            logger.error(
                "ATS persistence failed run_id=%s company_id=%s error_type=%s feed_url=%s",
                report.run_id,
                fetch_result.company_id,
                issue.exception_type,
                fetch_result.feed_url,
            )
            report.companies_failed += 1
            if provider_summary is not None:
                provider_summary.persistence_failures += 1
            continue
        report.companies_succeeded += 1
        report.jobs_upserted += len(jobs)
        if provider_summary is not None:
            provider_summary.jobs_upserted += len(jobs)

    return _finish_report(report, providers)


async def run_scan_locked() -> IngestionRunReport:
    """Run ingestion while holding one process-independent PostgreSQL lock."""
    lock_report = _new_report()
    try:
        async with engine.connect() as lock_connection:
            acquired = await lock_connection.scalar(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": INGESTION_LOCK_ID},
            )
            if not acquired:
                lock_report.status = RunStatus.SKIPPED
                _stamp_report(lock_report)
                logger.info(
                    "ATS ingestion run skipped run_id=%s reason=lock_held",
                    lock_report.run_id,
                )
                return lock_report

            try:
                async with AsyncSessionLocal() as db:
                    return await run_scan(db)
            finally:
                await lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": INGESTION_LOCK_ID},
                )
    except IngestionRunFailedError:
        raise
    except Exception as exc:
        _fail_report(lock_report, exc)
        logger.exception(
            "ATS ingestion lock/run setup failed run_id=%s error_type=%s",
            lock_report.run_id,
            type(exc).__name__,
        )
        raise IngestionRunFailedError(lock_report) from exc


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
