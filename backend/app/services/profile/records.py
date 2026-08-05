"""The profile row itself.

The profile is written with Core upserts, which bypass the ORM identity map.
With ``expire_on_commit=False`` a previously loaded instance would otherwise
come back with stale attributes, so the read here forces ``populate_existing``.
That subtlety is the reason this module exists — it is not generic CRUD.
"""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import messages
from app.exceptions import ProfileNotFoundError
from app.models.profile import Profile
from app.models.technology import ProfileTechnology


async def upsert_profile(db: AsyncSession, user_id: int, fields: dict) -> None:
    """Create the user's profile or update only the supplied fields."""
    statement = pg_insert(Profile).values(user_id=user_id, **fields)
    statement = statement.on_conflict_do_update(
        index_elements=[Profile.user_id],
        set_={**fields, "updated_at": func.now()},
    )
    await db.execute(statement)


async def load_profile(db: AsyncSession, user_id: int) -> Profile | None:
    return (
        await db.execute(
            select(Profile)
            .where(Profile.user_id == user_id)
            .options(selectinload(Profile.technologies).selectinload(ProfileTechnology.technology))
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()


async def profile_id(db: AsyncSession, user_id: int) -> int:
    """The profile's id, or a 404-mapped error before any write happens."""
    found = await db.scalar(select(Profile.id).where(Profile.user_id == user_id))
    if found is None:
        raise ProfileNotFoundError(messages.PROFILE_NOT_FOUND)
    return found
