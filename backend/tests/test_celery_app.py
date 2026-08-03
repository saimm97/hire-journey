"""Celery task discovery, routing, and schedule configuration."""

from app.celery_app import celery_app

INGESTION_TASK_NAME = "hire_journey.ingest_jobs"


def test_ingestion_task_is_discovered():
    celery_app.loader.import_default_modules()

    assert INGESTION_TASK_NAME in celery_app.tasks


def test_ingestion_task_uses_reliable_single_item_delivery():
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_routes[INGESTION_TASK_NAME] == {"queue": "ingestion"}


def test_ingestion_runs_twice_daily_in_utc():
    entry = celery_app.conf.beat_schedule["ingest_jobs_twice_daily"]
    schedule = entry["schedule"]

    assert celery_app.conf.timezone == "UTC"
    assert entry["task"] == INGESTION_TASK_NAME
    assert entry["options"] == {"queue": "ingestion"}
    assert schedule.minute == {0}
    assert schedule.hour == {7, 15}
