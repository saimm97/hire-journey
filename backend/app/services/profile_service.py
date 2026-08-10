"""Back-compatible facade over :mod:`app.services.profile`.

New code should import from ``app.services.profile``. This module keeps
``from app.services import profile_service`` working for the API layer, and
keeps route-level names patchable in tests (the routes resolve them through
this module at call time).
"""

from app.services.profile import (
    get_snapshot,
    is_onboarding_complete,
    normalize_technology,
    onboarding_completion_issues,
    process_cv,
    replace_employments,
    replace_projects,
    save_projects,
    set_profile_technologies,
    update_profile,
    upsert_profile,
)

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
