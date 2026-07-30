"""Provider fixtures exercised through HTTP fetching, parsing, and persistence."""

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.job import Job
from app.services import company_service, search_service
from app.sources import base as source_base

FIXTURES = Path(__file__).parent / "fixtures" / "ats"


def _fixture(name: str) -> object:
    with (FIXTURES / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


@pytest_asyncio.fixture
async def ingestion_company(db: AsyncSession) -> AsyncIterator:
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


async def _run_fixture(
    db: AsyncSession,
    company: Company,
    payload: object,
    monkeypatch,
) -> tuple[int, list[str]]:
    feed_url = company.careers_url
    requested_urls: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        assert str(request.url) == feed_url
        return httpx.Response(200, json=payload, request=request)

    async def only_fixture_company(_db: AsyncSession) -> list[Company]:
        return [company]

    monkeypatch.setattr(company_service, "get_scannable_companies", only_fixture_company)
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as provider_client:
        monkeypatch.setattr(source_base, "_client", provider_client)
        report = await search_service.run_scan(db)

    return report.jobs_upserted, requested_urls


async def test_greenhouse_fixture_is_ingested_end_to_end(
    db: AsyncSession,
    client,
    ingestion_company,
    monkeypatch,
):
    feed_url = (
        "https://boards-api.greenhouse.io/v1/boards/" "pytest-greenhouse-e2e/jobs?content=true"
    )
    company = await ingestion_company("Greenhouse Fixture", feed_url)
    company_name = company.name

    total, requested_urls = await _run_fixture(
        db,
        company,
        _fixture("greenhouse_jobs.json"),
        monkeypatch,
    )
    response = await client.get("/api/v1/jobs", params={"company": company_name})

    assert total == 1
    assert requested_urls == [feed_url]
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    job = body["results"][0]
    assert {
        "title": job["title"],
        "company_name": job["company_name"],
        "location": job["location"],
        "url": job["url"],
        "description": job["description"],
        "salary_min": job["salary_min"],
        "salary_max": job["salary_max"],
        "deadline": job["deadline"],
    } == {
        "title": "Senior Platform Engineer",
        "company_name": company_name,
        "location": "Remote — United States",
        "url": "https://boards.greenhouse.io/hijfixture/jobs/731001",
        "description": "<h2>About the role</h2><p>Build reliable systems.</p>",
        "salary_min": 150000,
        "salary_max": 185000,
        "deadline": "2026-08-15T23:59:59Z",
    }


async def test_lever_fixture_is_ingested_end_to_end(
    db: AsyncSession,
    client,
    ingestion_company,
    monkeypatch,
):
    feed_url = "https://api.lever.co/v0/postings/pytest-lever-e2e"
    company = await ingestion_company("Lever Fixture", feed_url)
    company_name = company.name

    total, requested_urls = await _run_fixture(
        db,
        company,
        _fixture("lever_jobs.json"),
        monkeypatch,
    )
    response = await client.get("/api/v1/jobs", params={"company": company_name})

    assert total == 1
    assert requested_urls == [feed_url]
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    job = body["results"][0]
    assert {
        "title": job["title"],
        "company_name": job["company_name"],
        "location": job["location"],
        "url": job["url"],
        "description": job["description"],
        "salary_min": job["salary_min"],
        "salary_max": job["salary_max"],
        "deadline": job["deadline"],
    } == {
        "title": "Backend Engineer",
        "company_name": company_name,
        "location": "New York, NY; Remote",
        "url": ("https://jobs.lever.co/hijfixture/" "a351b404-21f8-4dca-b64d-1104f3721cb4"),
        "description": (
            "<p>Build reliable services.</p><h3>Requirements</h3>"
            "<ul><li>Python</li><li>PostgreSQL</li></ul>"
            "<p>Equal opportunity employer.</p>"
        ),
        "salary_min": 105000,
        "salary_max": 145000,
        "deadline": None,
    }


async def test_ashby_fixture_is_ingested_end_to_end(
    db: AsyncSession,
    client,
    ingestion_company,
    monkeypatch,
):
    feed_url = (
        "https://api.ashbyhq.com/posting-api/job-board/" "pytest-ashby-e2e?includeCompensation=true"
    )
    company = await ingestion_company("Ashby Fixture", feed_url)
    company_name = company.name

    total, requested_urls = await _run_fixture(
        db,
        company,
        _fixture("ashby_jobs.json"),
        monkeypatch,
    )
    response = await client.get("/api/v1/jobs", params={"company": company_name})

    assert total == 1
    assert requested_urls == [feed_url]
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    job = body["results"][0]
    assert {
        "title": job["title"],
        "company_name": job["company_name"],
        "location": job["location"],
        "url": job["url"],
        "description": job["description"],
        "salary_min": job["salary_min"],
        "salary_max": job["salary_max"],
        "deadline": job["deadline"],
    } == {
        "title": "Product Engineer",
        "company_name": company_name,
        "location": "Remote; London, UK",
        "url": ("https://jobs.ashbyhq.com/hijfixture/" "f65f588e-e4d1-4476-b7af-6c82ef37ec90"),
        "description": ("<h2>The role</h2><p>Own <strong>important</strong> product systems.</p>"),
        "salary_min": 130000,
        "salary_max": 175000,
        "deadline": None,
    }
