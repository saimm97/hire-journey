"""Technology identity and a profile's overall skill set.

Technology rows are a shared vocabulary keyed on a lowercase-normalized name,
so they are upserted and never deleted here.
"""

from collections.abc import Iterable

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technology import ProfileTechnology, Technology


def normalize_technology(value: str) -> str:
    return " ".join(value.strip().casefold().split())


async def get_or_create_technology(db: AsyncSession, name: str) -> Technology:
    """Upsert a technology by its lowercase-normalized name."""
    normalized = normalize_technology(name)[:100]  # column limit; LLM output is unbounded
    statement = (
        pg_insert(Technology)
        .values(name=normalized)
        .on_conflict_do_update(index_elements=[Technology.name], set_={"name": normalized})
        .returning(Technology)
    )
    return (await db.execute(statement)).scalar_one()


async def set_profile_technologies(
    db: AsyncSession,
    profile_id: int,
    names: Iterable[str],
    *,
    replace: bool,
) -> None:
    if replace:
        await db.execute(
            delete(ProfileTechnology).where(ProfileTechnology.profile_id == profile_id)
        )
    for name in names:
        if not name.strip():
            continue
        technology = await get_or_create_technology(db, name)
        statement = (
            pg_insert(ProfileTechnology)
            .values(profile_id=profile_id, technology_id=technology.id)
            .on_conflict_do_nothing(
                index_elements=[ProfileTechnology.profile_id, ProfileTechnology.technology_id]
            )
        )
        await db.execute(statement)
