from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "hire_journey",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=60 * 60,
    broker_connection_retry_on_startup=True,
    task_routes={
        "hire_journey.ingest_jobs": {"queue": "ingestion"},
    },
    beat_schedule={
        "ingest_jobs_twice_daily": {
            "task": "hire_journey.ingest_jobs",
            "schedule": crontab(minute="0", hour="7,15"),
            "options": {"queue": "ingestion"},
        },
    },
)
