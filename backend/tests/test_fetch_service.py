"""Scheduling tests for provider-isolated ATS fetching."""

import asyncio
import logging
from contextlib import suppress

import httpx
import pytest

from app.models.company import Company
from app.services import fetch_service
from app.services.ingestion_report import IssueCode, IssueStage
from app.sources import SOURCES
from app.sources.base import ATSInvalidFeedError, ATSInvalidJSONError, ATSResponseTooLargeError


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


async def test_successful_company_fetch_is_debug_only(monkeypatch, caplog):
    company = Company(
        id=7,
        name="Quiet Success",
        slug="quiet-success",
        careers_url="https://api.lever.co/v0/postings/quiet-success",
    )

    async def fetch_success(_url: str, _company_name: str):
        return []

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fetch_success)
    caplog.set_level(logging.DEBUG, logger=fetch_service.__name__)

    result = (await fetch_service.fetch_all([company]))[0]

    assert result.succeeded
    success_records = [
        record for record in caplog.records if "ATS fetch succeeded" in record.message
    ]
    assert len(success_records) == 1
    assert success_records[0].levelno == logging.DEBUG


async def test_unroutable_feed_uses_the_invalid_url_taxonomy():
    company = Company(
        id=9,
        name="Unknown ATS",
        slug="unknown-ats",
        careers_url="https://careers.example.test/jobs",
    )

    result = (await fetch_service.fetch_all([company]))[0]

    assert not result.succeeded
    assert result.provider is None
    assert result.error is not None
    assert result.error.company_name == "Unknown ATS"
    assert result.error.stage is IssueStage.ROUTING
    assert result.error.code is IssueCode.INVALID_FEED_URL
    assert result.error.message == "The configured feed URL is invalid or unsupported."


_REQUEST = httpx.Request("GET", "https://api.lever.co/v0/postings/acme")


@pytest.mark.parametrize(
    ("provider_error", "code", "stage", "message", "http_status", "retryable"),
    [
        (
            httpx.ConnectError("private connection detail", request=_REQUEST),
            IssueCode.CONNECTION_FAILED,
            IssueStage.FETCH,
            "The provider connection failed.",
            None,
            True,
        ),
        (
            httpx.HTTPStatusError(
                "private HTTP detail",
                request=_REQUEST,
                response=httpx.Response(404, request=_REQUEST),
            ),
            IssueCode.PROVIDER_HTTP_ERROR,
            IssueStage.FETCH,
            "The provider feed returned HTTP 404.",
            404,
            False,
        ),
        (
            httpx.HTTPStatusError(
                "private rate-limit detail",
                request=_REQUEST,
                response=httpx.Response(429, request=_REQUEST),
            ),
            IssueCode.RATE_LIMITED,
            IssueStage.FETCH,
            "The provider rate limit was exhausted after retries.",
            429,
            True,
        ),
        (
            httpx.HTTPStatusError(
                "private service detail",
                request=_REQUEST,
                response=httpx.Response(503, request=_REQUEST),
            ),
            IssueCode.PROVIDER_HTTP_ERROR,
            IssueStage.FETCH,
            "The provider feed returned HTTP 503.",
            503,
            True,
        ),
        (
            ATSResponseTooLargeError("private response detail"),
            IssueCode.RESPONSE_TOO_LARGE,
            IssueStage.FETCH,
            "The provider response exceeded the configured size limit.",
            None,
            False,
        ),
        (
            ATSInvalidJSONError("private response body"),
            IssueCode.INVALID_JSON,
            IssueStage.PARSE,
            "The provider response was not valid JSON.",
            None,
            False,
        ),
        (
            ATSInvalidFeedError("private malformed payload"),
            IssueCode.INVALID_FEED,
            IssueStage.PARSE,
            "The provider response did not contain a valid job feed.",
            None,
            False,
        ),
        (
            RuntimeError("private unexpected detail"),
            IssueCode.UNEXPECTED_FETCH_ERROR,
            IssueStage.FETCH,
            "The provider feed could not be fetched.",
            None,
            False,
        ),
    ],
)
async def test_fetch_failures_use_safe_stable_taxonomy(
    monkeypatch,
    provider_error,
    code,
    stage,
    message,
    http_status,
    retryable,
):
    company = Company(
        id=42,
        name="Acme",
        slug="acme",
        careers_url="https://api.lever.co/v0/postings/acme",
    )

    async def fail_fetch(_url: str, _company_name: str):
        raise provider_error

    monkeypatch.setattr(SOURCES["lever"], "fetch_url", fail_fetch)

    result = (await fetch_service.fetch_all([company]))[0]

    assert not result.succeeded
    assert result.error is not None
    assert result.error.company_id == 42
    assert result.error.company_name == "Acme"
    assert result.error.provider == "lever"
    assert result.error.code is code
    assert result.error.stage is stage
    assert result.error.message == message
    assert result.error.http_status == http_status
    assert result.error.retryable is retryable
    assert "private" not in result.error.message
