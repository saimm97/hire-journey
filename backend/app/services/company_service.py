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
from app.sources import (
    build_job_feed_url,
    normalize_board_slug,
    supports_provider,
)

_YAML_PATH = Path(__file__).parent.parent.parent / "config" / "companies.yaml"


async def get_scannable_companies(db: AsyncSession) -> list[Company]:
    """Return companies with a validated, callable ATS feed configured."""
    result = await db.execute(
        select(Company).where(Company.careers_url.is_not(None)).order_by(Company.name)
    )
    return list(result.scalars().all())


async def seed_from_yaml(db: AsyncSession) -> dict[str, int]:
    """Upsert companies and their constructed ATS feed URLs. Idempotent.

    The YAML contains provider + slug rather than a duplicated full URL. URL
    construction and validation happen before each INSERT, and the same helper
    can be reused by future admin or bulk-import entry points.
    """
    with open(_YAML_PATH) as f:
        config = yaml.safe_load(f)

    # Validate and construct every URL before issuing the first statement. One
    # malformed future entry therefore cannot leave a partially executed seed
    # transaction for callers that choose to handle the validation error.
    seed_rows = []
    for entry in config.get("companies", []):
        provider = entry["source"].strip().lower()
        slug = normalize_board_slug(entry["slug"])
        seed_rows.append(
            {
                "name": entry["name"].strip(),
                "slug": slug,
                # Unsupported sources remain seedable but deliberately receive
                # no callable URL until their response parser is implemented.
                "careers_url": (
                    build_job_feed_url(provider, slug) if supports_provider(provider) else None
                ),
            }
        )

    companies_inserted = 0
    feed_urls_built = 0
    for entry in seed_rows:
        stmt = pg_insert(Company).values(
            name=entry["name"],
            slug=entry["slug"],
            careers_url=entry["careers_url"],
        )
        # A company may already exist as a resume employer without a slug —
        # in that case attach its source details instead of skipping.
        update_values = {"slug": entry["slug"]}
        if entry["careers_url"] is not None:
            update_values["careers_url"] = entry["careers_url"]
            feed_urls_built += 1
        stmt = stmt.on_conflict_do_update(constraint="uq_companies_name", set_=update_values)
        result = await db.execute(stmt)
        companies_inserted += result.rowcount

    await db.commit()
    return {
        "companies": companies_inserted,
        "feed_urls": feed_urls_built,
        "awaiting_adapter": len(seed_rows) - feed_urls_built,
    }
