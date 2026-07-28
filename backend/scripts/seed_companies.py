"""Seed the companies table from config/companies.yaml.

Run from backend/:
    python scripts/seed_companies.py

Safe to run multiple times — existing rows are updated with the configured slug
and the provider feed URL constructed from it.
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.services.company_service import seed_from_yaml


async def main() -> None:
    async with AsyncSessionLocal() as db:
        counts = await seed_from_yaml(db)
    print(
        f"Done — companies upserted: {counts['companies']}; "
        f"feed URLs built: {counts['feed_urls']}; "
        f"awaiting an adapter: {counts['awaiting_adapter']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
