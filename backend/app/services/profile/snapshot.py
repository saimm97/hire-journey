"""The onboarding read projection and the computed completion rule.

Completion is derived on every read and intentionally never persisted, so it
can never disagree with the underlying rows.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.resume import Resume
from app.schemas.profile import CompletionIssue, EmploymentRead, ResumeMeta
from app.schemas.project import ProjectRead
from app.services.profile import employment, projects, records
from app.utils.normalization import clean


def onboarding_completion_issues(profile: Profile) -> list[CompletionIssue]:
    """Return every unmet onboarding requirement in step order."""
    issues: list[CompletionIssue] = []
    requirements = (
        (
            profile.source_resume_id is not None,
            "profile",
            ["source_resume"],
            "Upload a resume.",
        ),
        (
            bool(clean(profile.first_name)),
            "profile",
            ["first_name"],
            "Enter your first name.",
        ),
        (
            bool(clean(profile.last_name)),
            "profile",
            ["last_name"],
            "Enter your last name.",
        ),
        (
            bool(clean(profile.title)),
            "profile",
            ["title"],
            "Enter your professional title.",
        ),
        (
            bool(profile.desired_roles),
            "preferences",
            ["desired_roles"],
            "Add at least one desired role.",
        ),
        (
            bool(profile.desired_locations),
            "preferences",
            ["desired_locations"],
            "Add at least one desired location.",
        ),
        (
            bool(profile.work_modes_preferred),
            "preferences",
            ["work_modes_preferred"],
            "Pick at least one work mode.",
        ),
        (
            bool(clean(profile.seniority_level)),
            "preferences",
            ["seniority_level"],
            "Pick your seniority level.",
        ),
    )
    for complete, step, path, message in requirements:
        if not complete:
            issues.append(CompletionIssue(step=step, path=path, message=message))
    return issues


def is_onboarding_complete(profile: Profile) -> bool:
    """The computed completion rule — intentionally never persisted."""
    return not onboarding_completion_issues(profile)


async def _source_resume_meta(db: AsyncSession, profile: Profile) -> ResumeMeta | None:
    if profile.source_resume_id is None:
        return None
    resume = await db.get(Resume, profile.source_resume_id)
    if resume is None:
        return None
    return ResumeMeta(
        id=resume.id,
        file_name=resume.file_name,
        created_at=resume.created_at,
        summary=(resume.parsed_content or {}).get("summary"),
    )


async def get_snapshot(
    db: AsyncSession, user_id: int
) -> tuple[Profile, ResumeMeta | None, list[EmploymentRead], list[ProjectRead]] | None:
    """Everything the onboarding UI needs, or None when no profile exists."""
    profile = await records.load_profile(db, user_id)
    if profile is None:
        return None
    return (
        profile,
        await _source_resume_meta(db, profile),
        await employment.load_employments(db, profile.id),
        await projects.load_projects(db, profile.id),
    )
