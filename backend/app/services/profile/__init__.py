"""Profile onboarding: read projection, human correction, and resume ingestion.

Application code should use the names re-exported here. The submodules are
internal seams — each owns one persistence invariant — and are imported
directly only by their siblings and by tests targeting a specific invariant:

    records      the profile row (Core upsert vs. the ORM identity map)
    technologies the shared technology vocabulary and a profile's skill set
    employment   company identity (advisory-locked) and employment rows
    projects     project identity, copy-on-write renames, orphan cleanup
    snapshot     the read projection and the computed completion rule
    correction   PATCH /profile — owns its transaction
    ingestion    POST /profile/cv — owns its transaction

Only correction and ingestion commit; every module below them stays inside
whatever transaction its caller opened.
"""

from app.services.profile.correction import update_profile
from app.services.profile.employment import replace_employments
from app.services.profile.ingestion import process_cv
from app.services.profile.projects import replace_projects, save_projects
from app.services.profile.records import upsert_profile
from app.services.profile.snapshot import (
    get_snapshot,
    is_onboarding_complete,
    onboarding_completion_issues,
)
from app.services.profile.technologies import normalize_technology, set_profile_technologies

__all__ = [
    "get_snapshot",
    "is_onboarding_complete",
    "normalize_technology",
    "onboarding_completion_issues",
    "process_cv",
    "replace_employments",
    "replace_projects",
    "save_projects",
    "set_profile_technologies",
    "update_profile",
    "upsert_profile",
]
