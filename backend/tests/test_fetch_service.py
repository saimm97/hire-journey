"""Scheduling tests for provider-isolated ATS fetching."""

import asyncio
from contextlib import suppress

from app.models.company import Company
from app.services import fetch_service
from app.sources import SOURCES


async def test_provider_wait_does_not_consume_global_slot(monkeypatch):
    greenhouse = Company(
        id=1,
        name="Blocked Greenhouse",
        slug="blocked-greenhouse",
        careers_url=(
            "https://boards-api.greenhouse.io/v1/boards/blocked-greenhouse/jobs?content=true"
        ),
    )
    lever = Company(
        id=2,
        name="Ready Lever",
        slug="ready-lever",
        careers_url="https://api.lever.co/v0/postings/ready-lever",
    )
    lever_started = asyncio.Event()

    async def fetch_lever(_url: str, _company_name: str):
        lever_started.set()
        return []

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fetch_lever)
    global_sem = asyncio.Semaphore(1)
    provider_sems = {
        "greenhouse": asyncio.Semaphore(0),
        "lever": asyncio.Semaphore(1),
    }

    blocked_task = asyncio.create_task(
        fetch_service._fetch_one(greenhouse, global_sem, provider_sems)
    )
    await asyncio.sleep(0)
    ready_result = await asyncio.wait_for(
        fetch_service._fetch_one(lever, global_sem, provider_sems),
        timeout=1,
    )

    assert lever_started.is_set()
    assert ready_result.succeeded

    blocked_task.cancel()
    with suppress(asyncio.CancelledError):
        await blocked_task
