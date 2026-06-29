"""Company and source DB operations.

Loads active companies for the fetch pipeline and provides the seed helper used
by scripts/seed_companies.py to populate the DB from companies.yaml.
"""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.source import Source

_YAML_PATH = Path(__file__).parent.parent.parent / "config" / "companies.yaml"

# Canonical source entries — name → base_url
_SOURCES = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board",
    "lever": "https://api.lever.co/v0/postings",
}


async def get_active_companies(db: AsyncSession) -> list[Company]:
    """Return all active companies with their source pre-loaded."""
    result = await db.execute(
        select(Company)
        .where(Company.is_active.is_(True))
        .options(selectinload(Company.source))
        .order_by(Company.name)
    )
    return list(result.scalars().all())


async def seed_from_yaml(db: AsyncSession) -> dict[str, int]:
    """Populate sources and companies from companies.yaml. Idempotent.

    Returns counts of rows inserted for sources and companies.
    """
    with open(_YAML_PATH) as f:
        config = yaml.safe_load(f)

    # 1. Upsert sources
    for source_name, base_url in _SOURCES.items():
        stmt = pg_insert(Source).values(name=source_name, base_url=base_url)
        stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
        await db.execute(stmt)
    await db.flush()

    # 2. Load source name → id map
    rows = await db.execute(select(Source.source_id, Source.name))
    source_map = {name: sid for sid, name in rows.all()}

    # 3. Upsert companies
    companies_inserted = 0
    for entry in config.get("companies", []):
        source_id = source_map.get(entry["source"])
        if source_id is None:
            continue
        stmt = pg_insert(Company).values(
            company_id=__import__("uuid").uuid4(),
            source_id=source_id,
            name=entry["name"],
            slug=entry["slug"],
            is_active=True,
        )
        stmt = stmt.on_conflict_do_nothing(constraint="uq_companies_source_slug")
        result = await db.execute(stmt)
        companies_inserted += result.rowcount

    await db.commit()
    return {"sources": len(_SOURCES), "companies": companies_inserted}
