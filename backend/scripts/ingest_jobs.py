"""Run one globally locked ATS ingestion pass.

Intended for a deployment scheduler, for example twice daily:
    python scripts/ingest_jobs.py

The PostgreSQL advisory lock lives on a dedicated connection for the complete
run. If another scheduler or deployment is already ingesting, this process exits
without issuing ATS requests.
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.services.search_service import IngestionAlreadyRunningError, run_scan_locked
from app.sources.base import close_client


async def main() -> None:
    try:
        total = await run_scan_locked()
        print(f"Done — jobs fetched and upserted: {total}")
    except IngestionAlreadyRunningError:
        print("Skipped — another job-ingestion run already holds the lock")
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())
