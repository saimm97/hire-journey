"""Human profile correction — the write path behind PATCH /profile.

This module owns the whole transaction. The section appliers below never
commit or roll back, which is what makes a combined update atomic: a project
ownership conflict raised while applying details also discards a preferences
write made in the same request.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.profile import PreferencesUpdate, ProfileDetailsUpdate, ProfileUpdate
from app.services.profile import employment, projects, records, technologies
from app.utils.normalization import clean


async def _apply_details(
    db: AsyncSession, user_id: int, profile_id: int, details: ProfileDetailsUpdate
) -> None:
    """Persist the details section (a full replacement of everything in it)."""
    links = {
        "github_url": details.social_links.github_url,
        "linkedin_url": details.social_links.linkedin_url,
        "portfolio_url": details.social_links.portfolio_url,
    }
    fields = {
        "first_name": clean(details.first_name),
        "last_name": clean(details.last_name),
        "phone_number": clean(details.phone_number),
        "location": clean(details.location),
        "title": clean(details.title),
        "summary": clean(details.summary),
        "social_links": {key: value for key, value in links.items() if value},
        "education": [entry.model_dump(mode="json") for entry in details.education],
        "certifications": [entry.model_dump(mode="json") for entry in details.certifications],
    }
    await records.upsert_profile(db, user_id, fields)
    # Only the top-level list becomes the profile's skill set; project-only
    # tech is deliberately not hoisted here (unlike ingestion, which unions
    # them) because this list is user-curated and hoisting would fight edits.
    await technologies.set_profile_technologies(db, profile_id, details.technologies, replace=True)
    await employment.replace_employments(db, profile_id, details.employment_history)
    await projects.save_projects(db, profile_id, details.projects)


async def _apply_preferences(
    db: AsyncSession, user_id: int, preferences: PreferencesUpdate
) -> None:
    """Persist the preferences section."""
    fields = {
        "minimum_salary": preferences.minimum_salary,
        "desired_roles": preferences.desired_roles,
        "desired_locations": preferences.desired_locations,
        "work_modes_preferred": list(preferences.work_modes_preferred),
        "seniority_level": preferences.seniority_level,
    }
    await records.upsert_profile(db, user_id, fields)


async def update_profile(db: AsyncSession, user_id: int, update: ProfileUpdate) -> None:
    """Apply either or both update sections in a single transaction."""
    try:
        profile_id = await records.profile_id(db, user_id)  # 404 before any writes
        if update.details is not None:
            await _apply_details(db, user_id, profile_id, update.details)
        if update.preferences is not None:
            await _apply_preferences(db, user_id, update.preferences)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
