"""Database-backed tests for migration-free, URL-idempotent ATS ingestion."""

import logging
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.models.company import Company
from app.models.job import Job
from app.services import company_service, job_service, search_service
from app.services.ingestion_report import (
    IngestionRunFailedError,
    IssueCode,
    IssueStage,
    RunStatus,
    SourceStatus,
)
from app.sources import SOURCES
from app.sources import base as source_base
from app.sources.base import RawJob


@pytest_asyncio.fixture
async def create_ingestion_company(db: AsyncSession) -> AsyncIterator:
    company_ids: list[int] = []

    async def create(name: str, careers_url: str) -> Company:
        company = Company(
            name=f"{name} {uuid.uuid4().hex[:10]}",
            slug=f"pytest-{uuid.uuid4().hex[:10]}",
            careers_url=careers_url,
        )
        db.add(company)
        await db.commit()
        await db.refresh(company)
        company_ids.append(company.id)
        return company

    try:
        yield create
    finally:
        if company_ids:
            await db.execute(delete(Job).where(Job.company_id.in_(company_ids)))
            await db.execute(delete(Company).where(Company.id.in_(company_ids)))
            await db.commit()


async def test_same_feed_called_twice_upserts_one_job(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
    caplog,
):
    feed_url = "https://boards-api.greenhouse.io/v1/boards/pytest-idempotent/jobs?content=true"
    company = await create_ingestion_company("Idempotent ATS", feed_url)
    calls: list[str] = []

    async def fetch_twice(
        url: str,
        *,
        allowed_hosts: tuple[str, ...] | None = None,
    ) -> dict:
        calls.append(url)
        revision = len(calls)
        assert allowed_hosts == ("boards-api.greenhouse.io",)
        job = {
            "id": 12345,
            "title": f"Platform Engineer v{revision}",
            "absolute_url": "https://boards.greenhouse.io/pytest-idempotent/jobs/12345",
            "location": {"name": "Remote"},
            "content": f"<p>Description revision {revision}</p>",
        }
        # A duplicate in one provider response must also collapse before SQL.
        return {"jobs": [job, job]}

    async def only_test_company(_db: AsyncSession) -> list[Company]:
        return [company]

    monkeypatch.setattr(source_base, "fetch_json", fetch_twice)
    monkeypatch.setattr(company_service, "get_scannable_companies", only_test_company)
    caplog.set_level(logging.INFO, logger=search_service.__name__)

    first_report = await search_service.run_scan(db)
    second_report = await search_service.run_scan(db)

    assert first_report.status is RunStatus.COMPLETED
    assert first_report.companies_attempted == 1
    assert first_report.companies_succeeded == 1
    assert first_report.companies_failed == 0
    assert first_report.empty_feeds == 0
    assert first_report.jobs_fetched == 1
    assert first_report.jobs_upserted == 1
    assert first_report.duration_ms >= 0
    assert first_report.finished_at >= first_report.started_at
    assert first_report.errors == []
    assert first_report.warnings == []
    assert len(first_report.providers) == 1
    assert first_report.providers[0].provider == "greenhouse"
    assert first_report.providers[0].source_status is SourceStatus.HEALTHY
    assert second_report.jobs_upserted == 1
    assert any(
        record.levelno == logging.INFO
        and "ATS ingestion provider summary" in record.message
        and str(first_report.run_id) in record.message
        for record in caplog.records
    )
    assert any(
        record.levelno == logging.INFO
        and "ATS ingestion run completed" in record.message
        and str(first_report.run_id) in record.message
        for record in caplog.records
    )

    stored = (await db.execute(select(Job).where(Job.company_id == company.id))).scalars().all()
    assert calls == [feed_url, feed_url]
    assert len(stored) == 1
    assert stored[0].url == "https://boards.greenhouse.io/pytest-idempotent/jobs/12345"
    assert stored[0].title == "Platform Engineer v2"
    assert stored[0].description == "<p>Description revision 2</p>"
    assert stored[0].parsed_desc is None


async def test_locked_run_returns_an_ephemeral_skipped_report(db: AsyncSession):
    async with engine.connect() as lock_connection:
        acquired = await lock_connection.scalar(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": search_service.INGESTION_LOCK_ID},
        )
        assert acquired
        try:
            report = await search_service.run_scan_locked()
        finally:
            await lock_connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": search_service.INGESTION_LOCK_ID},
            )

    assert report.status is RunStatus.SKIPPED
    assert report.companies_attempted == 0
    assert report.jobs_fetched == 0
    assert report.providers == []
    assert report.errors == []
    assert report.warnings == []
    assert report.finished_at >= report.started_at


async def test_fatal_run_failure_raises_with_a_safe_report(
    db: AsyncSession,
    monkeypatch,
):
    async def fail_company_discovery(_db: AsyncSession) -> list[Company]:
        raise RuntimeError("postgresql://private-database-detail")

    monkeypatch.setattr(company_service, "get_scannable_companies", fail_company_discovery)

    with pytest.raises(IngestionRunFailedError) as caught:
        await search_service.run_scan(db)

    report = caught.value.report
    assert report.status is RunStatus.FAILED
    assert len(report.errors) == 1
    error = report.errors[0]
    assert error.stage is IssueStage.RUN
    assert error.code is IssueCode.UNEXPECTED_RUN_ERROR
    assert error.message == "The ingestion run could not be completed."
    assert error.exception_type == "RuntimeError"
    assert "private-database-detail" not in error.message


async def test_description_is_sanitized_without_overwriting_parsed_metadata(
    db: AsyncSession,
    create_ingestion_company,
):
    company = await create_ingestion_company(
        "HTML Merge ATS",
        "https://api.lever.co/v0/postings/pytest-html-merge",
    )
    url = "https://jobs.lever.co/pytest-html-merge/job-1"
    stored = await job_service.upsert_jobs(
        db,
        [
            RawJob(
                title="Backend Engineer",
                url=url,
                company=company.name,
                location="Remote",
                description="<p>Old description</p>",
            )
        ],
        company.id,
    )
    stored[0].parsed_desc = {
        "required_skills": ["Python"],
    }
    await db.commit()

    refreshed = await job_service.upsert_jobs(
        db,
        [
            RawJob(
                title="Backend Engineer",
                url=url,
                company=company.name,
                location="Remote",
                description=(
                    '<h2 onclick="bad()">Requirements</h2><p>Python</p>' "<script>bad()</script>"
                ),
            )
        ],
        company.id,
    )
    await db.commit()

    assert refreshed[0].description == "<h2>Requirements</h2><p>Python</p>"
    assert refreshed[0].parsed_desc == {"required_skills": ["Python"]}


async def test_jobs_api_exposes_sanitized_html_in_description_only(
    db: AsyncSession,
    create_ingestion_company,
    client,
):
    company = await create_ingestion_company(
        "HTML API ATS",
        "https://api.ashbyhq.com/posting-api/job-board/pytest-html-api",
    )
    await job_service.upsert_jobs(
        db,
        [
            RawJob(
                title="Product Engineer",
                url="https://jobs.ashbyhq.com/pytest-html-api/job-1",
                company=company.name,
                location="Remote",
                description=(
                    '<h2 style="color:red">Requirements</h2><ul><li>Python</li></ul>'
                    "<script>bad()</script>"
                ),
            )
        ],
        company.id,
    )
    await db.commit()

    response = await client.get("/api/v1/jobs", params={"company": company.name})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["description"] == ("<h2>Requirements</h2><ul><li>Python</li></ul>")
    assert "description_html" not in body["results"][0]


async def test_ingestion_keeps_jobs_that_old_global_filters_rejected(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
):
    feed_url = "https://api.lever.co/v0/postings/pytest-unfiltered"
    company = await create_ingestion_company("Unfiltered ATS", feed_url)

    async def fetch_unfiltered(url: str, company_name: str) -> list[RawJob]:
        assert url == feed_url
        return [
            RawJob(
                title="Junior Sales Intern",
                url="https://jobs.lever.co/pytest-unfiltered/job-1",
                company=company_name,
                location="India",
                description="A valid public posting that matching may filter later.",
                source_name="lever",
            )
        ]

    async def only_test_company(_db: AsyncSession) -> list[Company]:
        return [company]

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fetch_unfiltered)
    monkeypatch.setattr(company_service, "get_scannable_companies", only_test_company)

    report = await search_service.run_scan(db)
    assert report.status is RunStatus.COMPLETED
    assert report.jobs_upserted == 1
    stored = await db.scalar(
        select(func.count()).select_from(Job).where(Job.company_id == company.id)
    )
    assert stored == 1


async def test_empty_feed_is_a_warning_not_a_failed_company(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
):
    company = await create_ingestion_company(
        "Empty ATS",
        "https://api.lever.co/v0/postings/pytest-empty",
    )
    company_id = company.id
    company_name = company.name

    async def fetch_empty(_url: str, _company_name: str) -> list[RawJob]:
        return []

    async def only_test_company(_db: AsyncSession) -> list[Company]:
        return [company]

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fetch_empty)
    monkeypatch.setattr(company_service, "get_scannable_companies", only_test_company)

    report = await search_service.run_scan(db)

    assert report.status is RunStatus.COMPLETED
    assert report.companies_attempted == 1
    assert report.companies_succeeded == 1
    assert report.companies_failed == 0
    assert report.empty_feeds == 1
    assert report.jobs_fetched == 0
    assert report.jobs_upserted == 0
    assert report.errors == []
    assert len(report.warnings) == 1
    warning = report.warnings[0]
    assert warning.company_id == company_id
    assert warning.company_name == company_name
    assert warning.provider == "lever"
    assert warning.stage is IssueStage.FETCH
    assert warning.code is IssueCode.EMPTY_FEED
    assert warning.message == "The provider returned a valid feed containing no jobs."
    assert report.providers[0].source_status is SourceStatus.WARNING
    assert report.providers[0].empty_feeds == 1


async def test_one_company_fetch_failure_does_not_discard_another(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
):
    failed = await create_ingestion_company(
        "Failed ATS",
        "https://boards-api.greenhouse.io/v1/boards/pytest-failed/jobs?content=true",
    )
    healthy = await create_ingestion_company(
        "Healthy ATS",
        "https://api.ashbyhq.com/posting-api/job-board/pytest-healthy",
    )
    failed_id = failed.id
    failed_name = failed.name

    async def fail_fetch(url: str, company_name: str) -> list[RawJob]:
        raise TimeoutError("provider timed out")

    async def healthy_fetch(url: str, company_name: str) -> list[RawJob]:
        return [
            RawJob(
                title="Backend Engineer",
                url="https://jobs.ashbyhq.com/pytest-healthy/job-1",
                company=company_name,
                location="Remote",
                description="Healthy source job",
                source_name="ashby",
            )
        ]

    async def test_companies(_db: AsyncSession) -> list[Company]:
        return [failed, healthy]

    monkeypatch.setattr(SOURCES["greenhouse"], "fetch_url", fail_fetch)
    monkeypatch.setattr(SOURCES["ashby"], "fetch_url", healthy_fetch)
    monkeypatch.setattr(company_service, "get_scannable_companies", test_companies)

    report = await search_service.run_scan(db)

    assert report.status is RunStatus.COMPLETED_WITH_ERRORS
    assert report.companies_attempted == 2
    assert report.companies_succeeded == 1
    assert report.companies_failed == 1
    assert report.jobs_fetched == 1
    assert report.jobs_upserted == 1
    assert report.warnings == []
    assert len(report.errors) == 1
    assert report.errors[0].company_id == failed_id
    assert report.errors[0].company_name == failed_name
    assert report.errors[0].provider == "greenhouse"
    assert report.errors[0].stage is IssueStage.FETCH
    assert report.errors[0].code is IssueCode.REQUEST_TIMEOUT
    assert report.errors[0].message == "The provider request timed out."
    assert report.errors[0].exception_type == "TimeoutError"
    assert report.errors[0].retryable is True
    assert report.errors[0].http_status is None
    assert {summary.provider: summary.source_status for summary in report.providers} == {
        "ashby": SourceStatus.HEALTHY,
        "greenhouse": SourceStatus.UNAVAILABLE,
    }
    failed_count = await db.scalar(
        select(func.count()).select_from(Job).where(Job.company_id == failed_id)
    )
    healthy_count = await db.scalar(
        select(func.count()).select_from(Job).where(Job.company_id == healthy.id)
    )
    assert failed_count == 0
    assert healthy_count == 1


async def test_provider_is_degraded_when_only_some_source_feeds_fail(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
):
    failed = await create_ingestion_company(
        "Degraded Lever Failure",
        "https://api.lever.co/v0/postings/pytest-degraded-failure",
    )
    healthy = await create_ingestion_company(
        "Degraded Lever Success",
        "https://api.lever.co/v0/postings/pytest-degraded-success",
    )

    async def fetch_one(url: str, company_name: str) -> list[RawJob]:
        if url.endswith("failure"):
            raise TimeoutError("provider timed out")
        return [
            RawJob(
                title="Platform Engineer",
                url="https://jobs.lever.co/pytest-degraded-success/job-1",
                company=company_name,
                location="Remote",
                source_name="lever",
            )
        ]

    async def test_companies(_db: AsyncSession) -> list[Company]:
        return [failed, healthy]

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fetch_one)
    monkeypatch.setattr(company_service, "get_scannable_companies", test_companies)

    report = await search_service.run_scan(db)

    assert report.status is RunStatus.COMPLETED_WITH_ERRORS
    assert len(report.providers) == 1
    provider = report.providers[0]
    assert provider.provider == "lever"
    assert provider.source_status is SourceStatus.DEGRADED
    assert provider.companies_attempted == 2
    assert provider.companies_succeeded == 1
    assert provider.companies_failed == 1


async def test_bulk_upsert_chunks_large_boards(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
):
    company = await create_ingestion_company(
        "Chunked ATS",
        "https://api.lever.co/v0/postings/pytest-chunked",
    )
    monkeypatch.setattr(job_service, "UPSERT_CHUNK_SIZE", 2)
    raw_jobs = [
        RawJob(
            title=f"Engineer {index}",
            url=f"https://jobs.lever.co/pytest-chunked/job-{index}",
            company=company.name,
            location="Remote",
        )
        for index in range(5)
    ]

    stored = await job_service.upsert_jobs(db, raw_jobs, company.id)
    await db.commit()
    assert len(stored) == 5
    count = await db.scalar(
        select(func.count()).select_from(Job).where(Job.company_id == company.id)
    )
    assert count == 5


async def test_successful_snapshot_normalizes_values_and_clears_missing_salary(
    db: AsyncSession,
    create_ingestion_company,
):
    company = await create_ingestion_company(
        "Bounded ATS",
        "https://api.lever.co/v0/postings/pytest-bounded",
    )
    raw = RawJob(
        title=f"  {'T' * 510}  ",
        url="  https://jobs.lever.co/pytest-bounded/job-1  ",
        company=company.name,
        location=f"  {'L' * 270}  ",
        salary_min=120_000,
        salary_max=175_000,
    )

    stored = await job_service.upsert_jobs(db, [raw], company.id)
    await db.commit()

    assert len(stored) == 1
    assert stored[0].title == "T" * 500
    assert stored[0].location == "L" * 255
    assert stored[0].url == "https://jobs.lever.co/pytest-bounded/job-1"
    assert stored[0].salary_min == 120_000
    assert stored[0].salary_max == 175_000

    refreshed = await job_service.upsert_jobs(
        db,
        [
            RawJob(
                title="Updated title",
                url="https://jobs.lever.co/pytest-bounded/job-1",
                company=company.name,
                location="Remote",
            )
        ],
        company.id,
    )
    await db.commit()
    assert len(refreshed) == 1
    assert refreshed[0].salary_min is None
    assert refreshed[0].salary_max is None


async def test_failed_fetch_preserves_existing_salary(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
):
    company = await create_ingestion_company(
        "Salary Preservation ATS",
        "https://api.lever.co/v0/postings/pytest-salary-preservation",
    )
    await job_service.upsert_jobs(
        db,
        [
            RawJob(
                title="Platform Engineer",
                url="https://jobs.lever.co/pytest-salary-preservation/job-1",
                company=company.name,
                location="Remote",
                salary_min=140_000,
                salary_max=180_000,
            )
        ],
        company.id,
    )
    await db.commit()

    async def fail_fetch(_url: str, _company_name: str) -> list[RawJob]:
        raise TimeoutError("provider timed out")

    async def only_test_company(_db: AsyncSession) -> list[Company]:
        return [company]

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fail_fetch)
    monkeypatch.setattr(company_service, "get_scannable_companies", only_test_company)

    report = await search_service.run_scan(db)
    assert report.status is RunStatus.COMPLETED_WITH_ERRORS
    assert report.jobs_upserted == 0
    assert report.errors[0].code is IssueCode.REQUEST_TIMEOUT
    stored = await db.scalar(
        select(Job).where(Job.url == "https://jobs.lever.co/pytest-salary-preservation/job-1")
    )
    assert stored is not None
    assert stored.salary_min == 140_000
    assert stored.salary_max == 180_000


async def test_persistence_failure_does_not_expire_later_company_results(
    db: AsyncSession,
    create_ingestion_company,
    monkeypatch,
):
    failed = await create_ingestion_company(
        "Persistence Failure ATS",
        "https://api.lever.co/v0/postings/pytest-persistence-failure",
    )
    healthy = await create_ingestion_company(
        "Persistence Healthy ATS",
        "https://api.lever.co/v0/postings/pytest-persistence-healthy",
    )
    failed_id = failed.id
    failed_name = failed.name
    healthy_id = healthy.id

    async def fetch_one(url: str, company_name: str) -> list[RawJob]:
        return [
            RawJob(
                title="Backend Engineer",
                url=f"https://jobs.lever.co/{url.rsplit('/', 1)[-1]}/job-1",
                company=company_name,
                location="Remote",
            )
        ]

    async def test_companies(_db: AsyncSession) -> list[Company]:
        return [failed, healthy]

    original_upsert_jobs = job_service.upsert_jobs

    async def fail_first_upsert(
        session: AsyncSession,
        raw_jobs: list[RawJob],
        company_id: int,
    ) -> list[Job]:
        if company_id == failed_id:
            raise RuntimeError("simulated persistence failure")
        return await original_upsert_jobs(session, raw_jobs, company_id)

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fetch_one)
    monkeypatch.setattr(company_service, "get_scannable_companies", test_companies)
    monkeypatch.setattr(job_service, "upsert_jobs", fail_first_upsert)

    report = await search_service.run_scan(db)

    assert report.status is RunStatus.COMPLETED_WITH_ERRORS
    assert report.companies_attempted == 2
    assert report.companies_succeeded == 1
    assert report.companies_failed == 1
    assert report.jobs_fetched == 2
    assert report.jobs_upserted == 1
    assert len(report.errors) == 1
    error = report.errors[0]
    assert error.company_id == failed_id
    assert error.company_name == failed_name
    assert error.provider == "lever"
    assert error.stage is IssueStage.PERSISTENCE
    assert error.code is IssueCode.PERSISTENCE_FAILED
    assert error.message == "The fetched jobs could not be persisted."
    assert error.exception_type == "RuntimeError"
    assert "simulated persistence failure" not in error.message
    assert len(report.providers) == 1
    provider = report.providers[0]
    assert provider.provider == "lever"
    assert provider.source_status is SourceStatus.HEALTHY
    assert provider.companies_attempted == 2
    assert provider.companies_succeeded == 2
    assert provider.companies_failed == 0
    assert provider.persistence_failures == 1
    assert (
        await db.scalar(select(func.count()).select_from(Job).where(Job.company_id == failed_id))
        == 0
    )
    assert (
        await db.scalar(select(func.count()).select_from(Job).where(Job.company_id == healthy_id))
        == 1
    )
