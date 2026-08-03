"""Celery adapter behavior around the globally locked ingestion Module."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.search_service import IngestionAlreadyRunningError
from app.tasks import ingestion


def _patch_resources(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock]:
    close_client = AsyncMock()
    dispose_engine = AsyncMock()
    monkeypatch.setattr(ingestion, "close_client", close_client)
    monkeypatch.setattr(
        ingestion,
        "engine",
        SimpleNamespace(dispose=dispose_engine),
    )
    return close_client, dispose_engine


def test_ingestion_task_returns_completed_result_and_cleans_up(monkeypatch):
    run_scan_locked = AsyncMock(return_value=17)
    monkeypatch.setattr(ingestion, "run_scan_locked", run_scan_locked)
    close_client, dispose_engine = _patch_resources(monkeypatch)

    result = ingestion.ingest_jobs_task.run()

    assert result == {"status": "completed", "jobs_upserted": 17}
    run_scan_locked.assert_awaited_once_with()
    close_client.assert_awaited_once_with()
    dispose_engine.assert_awaited_once_with()


def test_ingestion_task_treats_lock_contention_as_a_skip(monkeypatch):
    run_scan_locked = AsyncMock(side_effect=IngestionAlreadyRunningError)
    monkeypatch.setattr(ingestion, "run_scan_locked", run_scan_locked)
    close_client, dispose_engine = _patch_resources(monkeypatch)

    result = ingestion.ingest_jobs_task.run()

    assert result == {"status": "skipped", "jobs_upserted": 0}
    close_client.assert_awaited_once_with()
    dispose_engine.assert_awaited_once_with()


def test_ingestion_task_propagates_failures_after_cleanup(monkeypatch):
    run_scan_locked = AsyncMock(side_effect=RuntimeError("scan failed"))
    monkeypatch.setattr(ingestion, "run_scan_locked", run_scan_locked)
    close_client, dispose_engine = _patch_resources(monkeypatch)

    with pytest.raises(RuntimeError, match="scan failed"):
        ingestion.ingest_jobs_task.run()

    close_client.assert_awaited_once_with()
    dispose_engine.assert_awaited_once_with()


def test_ingestion_task_disposes_engine_when_http_cleanup_fails(monkeypatch):
    monkeypatch.setattr(ingestion, "run_scan_locked", AsyncMock(return_value=4))
    close_client, dispose_engine = _patch_resources(monkeypatch)
    close_client.side_effect = RuntimeError("HTTP cleanup failed")

    with pytest.raises(RuntimeError, match="HTTP cleanup failed"):
        ingestion.ingest_jobs_task.run()

    dispose_engine.assert_awaited_once_with()
