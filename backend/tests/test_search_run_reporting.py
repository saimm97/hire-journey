"""The manual search-run route must not expose operator ingestion details."""

from datetime import datetime, timezone
from uuid import UUID

from app.services import search_service
from app.services.ingestion_report import (
    IngestionIssue,
    IngestionRunReport,
    IssueCode,
    IssueStage,
    RunStatus,
)


def _report(status: RunStatus) -> IngestionRunReport:
    now = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    return IngestionRunReport(
        run_id=UUID("b61a8a82-68b0-4e40-a994-1cb27523ff22"),
        status=status,
        started_at=now,
        finished_at=now,
        duration_ms=10,
        companies_attempted=2,
        companies_succeeded=1,
        companies_failed=1,
        jobs_fetched=7,
        jobs_upserted=7,
        errors=[
            IngestionIssue(
                company_id=42,
                company_name="Internal Company",
                provider="greenhouse",
                feed_url=("https://boards-api.greenhouse.io/v1/boards/internal-company/jobs"),
                stage=IssueStage.FETCH,
                code=IssueCode.PROVIDER_HTTP_ERROR,
                message="The provider feed returned HTTP 404.",
                http_status=404,
            )
        ],
    )


async def test_search_run_keeps_operator_details_out_of_the_response(client, monkeypatch):
    async def partial_run() -> IngestionRunReport:
        return _report(RunStatus.COMPLETED_WITH_ERRORS)

    monkeypatch.setattr(search_service, "run_scan_locked", partial_run)

    response = await client.post("/api/v1/search/run")

    assert response.status_code == 202
    assert response.json() == {"total_jobs_fetched": 7}
    assert "Internal Company" not in response.text
    assert "provider_http_error" not in response.text
    assert "internal-company/jobs" not in response.text
    assert "b61a8a82" not in response.text


async def test_search_run_preserves_lock_conflict_behavior(client, monkeypatch):
    async def skipped_run() -> IngestionRunReport:
        return _report(RunStatus.SKIPPED)

    monkeypatch.setattr(search_service, "run_scan_locked", skipped_run)

    response = await client.post("/api/v1/search/run")

    assert response.status_code == 409
    assert "already active" in response.text
    assert "Internal Company" not in response.text
