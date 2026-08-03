import asyncio
import logging

from app.celery_app import celery_app
from app.database import engine
from app.services.search_service import (
    IngestionAlreadyRunningError,
    run_scan_locked,
)
from app.sources.base import close_client

logger = logging.getLogger(__name__)


async def _run_ingestion() -> dict[str, str | int]:
    try:
        total = await run_scan_locked()
        logger.info("Scheduled job ingestion completed jobs_upserted=%d", total)
        return {
            "status": "completed",
            "jobs_upserted": total,
        }
    except IngestionAlreadyRunningError:
        logger.info("Scheduled job ingestion skipped reason=lock_held")
        return {
            "status": "skipped",
            "jobs_upserted": 0,
        }
    finally:
        # Both resources can be bound to the asyncio event loop created below.
        # Dispose them before asyncio.run() closes that loop.
        try:
            await close_client()
        finally:
            await engine.dispose()


@celery_app.task(name="hire_journey.ingest_jobs")
def ingest_jobs_task() -> dict[str, str | int]:
    return asyncio.run(_run_ingestion())
