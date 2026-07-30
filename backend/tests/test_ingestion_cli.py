"""Operator-facing rendering and exit behavior for ingestion reports."""

import json
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.services.ingestion_report import (
    IngestionIssue,
    IngestionRunReport,
    IssueCode,
    IssueStage,
    ProviderIngestionHealth,
    ProviderRunSummary,
    RunStatus,
)
from scripts import ingest_jobs as ingestion_cli
from scripts.ingest_jobs import exit_code_for, render_human, render_json


def _report(status: RunStatus = RunStatus.COMPLETED_WITH_ERRORS) -> IngestionRunReport:
    started_at = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 7, 30, 8, 1, 42, tzinfo=timezone.utc)
    return IngestionRunReport(
        run_id=UUID("b61a8a82-68b0-4e40-a994-1cb27523ff22"),
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=102_000,
        companies_attempted=3,
        companies_succeeded=1,
        companies_failed=2,
        empty_feeds=1,
        jobs_fetched=20,
        jobs_upserted=20,
        providers=[
            ProviderRunSummary(
                provider="greenhouse",
                ingestion_health=ProviderIngestionHealth.DEGRADED,
                feeds_attempted=3,
                feeds_succeeded=1,
                feeds_failed=2,
                empty_feeds=1,
                jobs_fetched=20,
                jobs_upserted=20,
            )
        ],
        warnings=[
            IngestionIssue(
                company_id=3,
                company_name="Empty Co",
                provider="greenhouse",
                feed_url="https://boards-api.greenhouse.io/v1/boards/empty-co/jobs",
                stage=IssueStage.FETCH,
                code=IssueCode.EMPTY_FEED,
                message="The provider returned a valid feed containing no jobs.",
            )
        ],
        errors=[
            IngestionIssue(
                company_id=1,
                company_name="Anthropic",
                provider="greenhouse",
                feed_url="https://boards-api.greenhouse.io/v1/boards/example-one/jobs",
                stage=IssueStage.FETCH,
                code=IssueCode.PROVIDER_HTTP_ERROR,
                message="The provider feed returned HTTP 404.",
                exception_type="HTTPStatusError",
                http_status=404,
            ),
            IngestionIssue(
                company_id=2,
                company_name="Acme",
                provider="greenhouse",
                feed_url="https://boards-api.greenhouse.io/v1/boards/example-two/jobs",
                stage=IssueStage.FETCH,
                code=IssueCode.PROVIDER_HTTP_ERROR,
                message="The provider feed returned HTTP 404.",
                exception_type="HTTPStatusError",
                http_status=404,
            ),
        ],
    )


def test_json_output_contains_the_complete_structured_report():
    payload = json.loads(render_json(_report()))

    assert payload["run_id"] == "b61a8a82-68b0-4e40-a994-1cb27523ff22"
    assert payload["status"] == "completed_with_errors"
    assert payload["started_at"] == "2026-07-30T08:00:00Z"
    assert payload["finished_at"] == "2026-07-30T08:01:42Z"
    assert payload["duration_ms"] == 102000
    assert payload["providers"][0] == {
        "provider": "greenhouse",
        "ingestion_health": "degraded",
        "feeds_attempted": 3,
        "feeds_succeeded": 1,
        "feeds_failed": 2,
        "empty_feeds": 1,
        "persistence_failures": 0,
        "jobs_fetched": 20,
        "jobs_upserted": 20,
    }
    assert payload["warnings"][0] == {
        "stage": "fetch",
        "code": "empty_feed",
        "message": "The provider returned a valid feed containing no jobs.",
        "company_id": 3,
        "company_name": "Empty Co",
        "provider": "greenhouse",
        "feed_url": "https://boards-api.greenhouse.io/v1/boards/empty-co/jobs",
        "exception_type": None,
        "http_status": None,
        "retry_eligible": False,
    }
    assert payload["errors"][0]["feed_url"].endswith("/example-one/jobs")
    assert payload["errors"][0]["http_status"] == 404
    assert "retryable" not in payload["errors"][0]


def test_human_output_groups_repeated_company_failures():
    output = render_human(_report())

    assert "Run: b61a8a82-68b0-4e40-a994-1cb27523ff22" in output
    assert "Status: completed_with_errors" in output
    assert "Duration: 1m 42s" in output
    assert "Companies: 3 attempted, 1 succeeded, 2 failed, 1 empty" in output
    assert "Jobs: 20 fetched, 20 upserted" in output
    assert "greenhouse" in output
    assert "health=degraded" in output
    assert "feeds=3" in output
    assert "greenhouse / provider_http_error (2)" in output
    assert "Anthropic: The provider feed returned HTTP 404." in output
    assert "feed: https://boards-api.greenhouse.io/v1/boards/example-one/jobs" in output
    assert "Acme: The provider feed returned HTTP 404." in output
    assert "Warnings:" in output
    assert "Empty Co: The provider returned a valid feed containing no jobs." in output


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (RunStatus.COMPLETED, 0),
        (RunStatus.SKIPPED, 0),
        (RunStatus.COMPLETED_WITH_ERRORS, 1),
        (RunStatus.FAILED, 1),
    ],
)
def test_exit_code_signals_unhealthy_runs(status: RunStatus, expected: int):
    assert exit_code_for(_report(status)) == expected


async def test_run_command_prints_partial_report_and_closes_client(
    monkeypatch,
    capsys,
):
    report = _report(RunStatus.COMPLETED_WITH_ERRORS)
    closed = False

    async def partial_run() -> IngestionRunReport:
        return report

    async def close() -> None:
        nonlocal closed
        closed = True

    monkeypatch.setattr(ingestion_cli, "run_scan_locked", partial_run)
    monkeypatch.setattr(ingestion_cli, "close_client", close)

    result = await ingestion_cli.run_command(json_output=True)

    assert result == 1
    assert json.loads(capsys.readouterr().out)["status"] == "completed_with_errors"
    assert closed is True


async def test_run_command_prints_fatal_report_before_returning_failure(
    monkeypatch,
    capsys,
):
    report = _report(RunStatus.FAILED)

    async def fatal_run() -> IngestionRunReport:
        raise ingestion_cli.IngestionRunFailedError(report)

    async def close() -> None:
        return None

    monkeypatch.setattr(ingestion_cli, "run_scan_locked", fatal_run)
    monkeypatch.setattr(ingestion_cli, "close_client", close)

    result = await ingestion_cli.run_command()

    output = capsys.readouterr().out
    assert result == 1
    assert "Status: failed" in output
    assert "Errors:" in output
