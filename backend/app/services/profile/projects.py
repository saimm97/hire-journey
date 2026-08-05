"""Project identity and a profile's memberships.

A ``Project`` row is a shared identity; ``ProfileProject`` is one profile's
link to it. Two write paths with deliberately different rules:

* ``replace_projects`` — resume ingestion. No ownership check (the extraction
  can't reference someone else's row), wipes every membership, dedupes by
  normalized name because the LLM surfaces the same project twice.
* ``save_projects`` — human correction. Ownership is enforced, renaming a
  shared project copies-on-write, omitted memberships are removed.

Both orphan-delete projects left with no memberships.
"""

from collections.abc import Iterable

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import messages
from app.exceptions import ProjectOwnershipError
from app.models.project import ProfileProject, ProfileProjectTechnology, Project
from app.schemas.extraction import ProjectItem
from app.schemas.profile import ProjectEntry
from app.schemas.project import ProjectRead
from app.services.profile import technologies
from app.utils.normalization import clean, clip, normalize_url


def _project_read(membership: ProfileProject, project: Project) -> ProjectRead:
    return ProjectRead(
        project_id=project.id,
        name=project.name,
        summary=membership.summary,
        tech_stack=[link.technology.name for link in membership.technologies],
        github_url=membership.github_url,
        deployed_url=membership.deployed_url,
    )


async def _load_memberships(
    db: AsyncSession, profile_id: int
) -> list[tuple[ProfileProject, Project]]:
    rows = (
        await db.execute(
            select(ProfileProject, Project)
            .join(Project, Project.id == ProfileProject.project_id)
            .where(ProfileProject.profile_id == profile_id)
            .options(
                selectinload(ProfileProject.technologies).selectinload(
                    ProfileProjectTechnology.technology
                )
            )
            .order_by(ProfileProject.created_at)
        )
    ).all()
    return [(membership, project) for membership, project in rows]


async def load_projects(db: AsyncSession, profile_id: int) -> list[ProjectRead]:
    return [
        _project_read(membership, project)
        for membership, project in await _load_memberships(db, profile_id)
    ]


def _project_url(value: str | None) -> str | None:
    """Normalized URL, dropped when malformed or over the column limit."""
    url = normalize_url(value)
    return url if url and len(url) <= 255 else None


async def _set_membership_technologies(
    db: AsyncSession, profile_project_id: int, names: Iterable[str]
) -> None:
    await db.execute(
        delete(ProfileProjectTechnology).where(
            ProfileProjectTechnology.profile_project_id == profile_project_id
        )
    )
    for name in names:
        if not name.strip():
            continue
        technology = await technologies.get_or_create_technology(db, name)
        await db.execute(
            pg_insert(ProfileProjectTechnology)
            .values(profile_project_id=profile_project_id, technology_id=technology.id)
            .on_conflict_do_nothing(
                index_elements=[
                    ProfileProjectTechnology.profile_project_id,
                    ProfileProjectTechnology.technology_id,
                ]
            )
        )


async def _create_membership(
    db: AsyncSession, profile_id: int, parsed: ProjectItem | ProjectEntry
) -> None:
    project = Project(name=clip(parsed.name, 255))
    db.add(project)
    await db.flush()
    membership = ProfileProject(
        profile_id=profile_id,
        project_id=project.id,
        summary=clean(parsed.summary),
        github_url=_project_url(parsed.github_url),
        deployed_url=_project_url(parsed.deployed_url),
    )
    db.add(membership)
    await db.flush()
    await _set_membership_technologies(db, membership.id, parsed.technologies)


async def replace_projects(db: AsyncSession, profile_id: int, projects: list[ProjectItem]) -> None:
    """Replace a profile's project memberships and remove unreferenced projects."""
    old_project_ids = list(
        (
            await db.scalars(
                select(ProfileProject.project_id).where(ProfileProject.profile_id == profile_id)
            )
        ).all()
    )
    await db.execute(delete(ProfileProject).where(ProfileProject.profile_id == profile_id))
    if old_project_ids:
        await db.execute(
            delete(Project).where(
                Project.id.in_(old_project_ids),
                ~exists().where(ProfileProject.project_id == Project.id),
            )
        )
    # The LLM can surface the same project from two resume sections; dedupe
    # by normalized name (first occurrence wins) so one profile never gets
    # duplicate identities from a single extraction.
    seen_names: set[str] = set()
    for parsed in projects:
        name = clean(parsed.name)
        if not name:
            continue
        key = " ".join(name.lower().split())
        if key in seen_names:
            continue
        seen_names.add(key)
        await _create_membership(db, profile_id, parsed)


async def save_projects(db: AsyncSession, profile_id: int, entries: list[ProjectEntry]) -> None:
    """Reconcile the profile's projects against the edited full set.

    project_id present -> edit (must belong to this profile); absent -> new
    identity. Renaming a project shared with another profile copies-on-write
    instead of mutating it. Omitted memberships are removed, and projects
    left with no memberships are deleted.
    """
    memberships = {
        project.id: (membership, project)
        for membership, project in await _load_memberships(db, profile_id)
    }
    for row_index, entry in enumerate(entries):
        if entry.project_id is not None and entry.project_id not in memberships:
            raise ProjectOwnershipError(messages.PROJECT_NOT_OWNED, row_index)

    handled: set[int] = set()
    for entry in entries:
        if entry.project_id is None:
            await _create_membership(db, profile_id, entry)
            continue
        membership, project = memberships[entry.project_id]
        handled.add(entry.project_id)
        name = entry.name.strip()
        shared = bool(
            await db.scalar(
                select(func.count())
                .select_from(ProfileProject)
                .where(
                    ProfileProject.project_id == project.id,
                    ProfileProject.id != membership.id,
                )
            )
        )
        if shared and name != project.name:
            # Copy-on-write: never rename a project another profile references.
            await db.delete(membership)
            await db.flush()
            await _create_membership(db, profile_id, entry)
            continue
        project.name = name
        membership.summary = clean(entry.summary)
        membership.github_url = entry.github_url
        membership.deployed_url = entry.deployed_url
        await db.flush()
        await _set_membership_technologies(db, membership.id, entry.technologies)

    for project_id in sorted(set(memberships) - handled):
        membership, project = memberships[project_id]
        await db.delete(membership)
        await db.flush()
        remaining = await db.scalar(
            select(func.count())
            .select_from(ProfileProject)
            .where(ProfileProject.project_id == project_id)
        )
        if not remaining:
            await db.delete(project)
    await db.flush()