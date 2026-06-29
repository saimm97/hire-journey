"""Seed the companies and sources tables from config/companies.yaml.

Run from backend/:
    python scripts/seed_companies.py

Safe to run multiple times — uses ON CONFLICT DO NOTHING so existing rows are
untouched.
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
    print(f"Done — sources: {counts['sources']}, companies inserted: {counts['companies']}")


if __name__ == "__main__":
    asyncio.run(main())
