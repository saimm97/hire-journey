"""In-process background scheduler for the job pipeline.

APScheduler runs `run_pipeline()` on a fixed interval (`settings.scan_interval_hours`),
plus once shortly after startup so a fresh boot doesn't wait a full interval for the
first scan.

This lives inside the FastAPI process (simplest for a single instance). If the app is
ever run as multiple replicas, each replica would start its own timer — see the note on
`scan_interval_hours` in config.py.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def run_pipeline() -> None:
    """One scheduled pipeline run.

    Placeholder for now — it only proves the timer fires. Real work comes next:
      Step A: collect jobs from all ATS boards  -> upsert into `jobs`
      Step B: score saved jobs per active user  -> upsert into `job_scores`
    """
    logger.info("pipeline tick — scheduler fired run_pipeline()")


def start_scheduler() -> None:
    """Start the background timer. Idempotent — safe to call once on startup."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_pipeline,
        trigger=IntervalTrigger(hours=settings.scan_interval_hours),
        id="job_pipeline",
        next_run_time=datetime.now(timezone.utc),  # also run once right after boot
        max_instances=1,  # never let two runs overlap
        coalesce=True,     # if runs pile up (e.g. app was asleep), collapse to one
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started — job_pipeline runs every %g h", settings.scan_interval_hours
    )


def stop_scheduler() -> None:
    """Stop the background timer on app shutdown."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
