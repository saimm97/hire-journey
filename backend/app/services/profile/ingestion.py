"""Resume ingestion — the write path behind POST /profile/cv.

Owns its whole transaction; the persistence modules it calls never commit.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.schemas.extraction import ResumeExtraction
from app.schemas.project import ProjectRead
from app.services import resume_service
from app.services.profile import employment, projects, records, technologies
from app.utils import document_parser, llm, prompts
from app.utils.normalization import clean, clip, normalize_url


def _resume_profile_values(extraction: ResumeExtraction) -> dict:
    """Map an extraction onto profile columns.

    Every resume-derived key is always present, so a re-upload overwrites
    stale values — clearing ones the new resume no longer contains. The
    preference fields are never touched. Education/certification entries
    without their required field are dropped here but survive verbatim in
    resumes.parsed_content.
    """
    social_links = {
        key: normalize_url(value)
        for key, value in {
            "github_url": extraction.github_url,
            "linkedin_url": extraction.linkedin_url,
            "portfolio_url": extraction.portfolio_url,
        }.items()
    }
    return {
        "first_name": clip(extraction.first_name, 100),
        "last_name": clip(extraction.last_name, 100),
        "phone_number": clip(extraction.phone_number, 50),
        "location": clip(extraction.location, 255),
        "title": clip(extraction.title, 255),
        "summary": clean(extraction.summary),
        "social_links": {key: value for key, value in social_links.items() if value},
        "education": [
            item.model_dump(mode="json") for item in extraction.education if clean(item.institution)
        ],
        "certifications": [
            item.model_dump(mode="json") for item in extraction.certifications if clean(item.name)
        ],
    }


async def process_cv(
    db: AsyncSession,
    user_id: int,
    file_name: str,
    data: bytes,
    replace_resume_id: int | None = None,
) -> tuple[Profile, list[ProjectRead], str | None]:
    """Parse a resume, LLM-extract it, and persist everything in one transaction."""
    # Parsing and extraction run BEFORE any DB writes: the LLM call takes
    # seconds and must never execute while holding the user row lock.
    text_content = document_parser.to_text(data, file_name)
    extraction = await llm.structured_extract(
        prompts.RESUME_EXTRACTION_SYSTEM, text_content, ResumeExtraction
    )
    # The raw, un-normalized extraction is preserved verbatim; persistence
    # below normalizes and filters, but nothing is lost.
    parsed_content = extraction.model_dump(mode="json")

    try:
        if replace_resume_id is None:
            resume = await resume_service.create_resume(
                db,
                user_id=user_id,
                file_name=file_name,
                raw_content=text_content,
                parsed_content=parsed_content,
            )
        else:
            resume = await resume_service.replace_resume(
                db,
                user_id=user_id,
                resume_id=replace_resume_id,
                file_name=file_name,
                raw_content=text_content,
                parsed_content=parsed_content,
            )

        fields = _resume_profile_values(extraction)
        fields["source_resume_id"] = resume.id
        await records.upsert_profile(db, user_id, fields)
        profile_id = await records.profile_id(db, user_id)
        # profile_technologies is the candidate's overall skill set, so it must
        # be a superset of every project's tech — the LLM fills the top-level
        # and per-project lists independently, so union them here rather than
        # trusting it to hoist project-only tech up itself. (Order-stable
        # de-dup; get_or_create_technology normalizes casing on top of this.)
        overall_technologies = list(
            dict.fromkeys(
                extraction.technologies
                + [tech for project in extraction.projects for tech in project.technologies]
            )
        )
        await technologies.set_profile_technologies(
            db, profile_id, overall_technologies, replace=True
        )
        await employment.replace_employments(db, profile_id, extraction.employment_history)
        await projects.replace_projects(db, profile_id, extraction.projects)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    profile = await records.load_profile(db, user_id)
    assert profile is not None
    return profile, await projects.load_projects(db, profile.id), extraction.summary
