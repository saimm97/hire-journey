"""Company DB operations.

Loads scannable companies for the fetch pipeline and provides the seed helper
used by scripts/seed_companies.py to populate the DB from companies.yaml.
"""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company

_YAML_PATH = Path(__file__).parent.parent.parent / "config" / "companies.yaml"


async def get_scannable_companies(db: AsyncSession) -> list[Company]:
    """Return all companies that have an ATS slug to scan."""
    result = await db.execute(
        select(Company).where(Company.slug.is_not(None)).order_by(Company.name)
    )
    return list(result.scalars().all())


async def seed_from_yaml(db: AsyncSession) -> dict[str, int]:
    """Populate companies from companies.yaml. Idempotent.

    Returns the count of company rows inserted.
    """
    with open(_YAML_PATH) as f:
        config = yaml.safe_load(f)

    companies_inserted = 0
    for entry in config.get("companies", []):
        stmt = pg_insert(Company).values(name=entry["name"], slug=entry["slug"])
        # A company may already exist as a resume employer without a slug —
        # in that case attach the slug instead of skipping.
        stmt = stmt.on_conflict_do_update(
            constraint="uq_companies_name",
            set_={"slug": entry["slug"]},
        )
        result = await db.execute(stmt)
        companies_inserted += result.rowcount

    await db.commit()
    return {"companies": companies_inserted}
