"""Profile endpoint: build the user's profile from an uploaded resume document."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import DocumentParseError, ExtractionError
from app.models.candidate import Candidate
from app.models.project import Project
from app.models.user import User
from app.schemas.profile import CVUploadResult, ProfileRead, ProfileUpdate
from app.schemas.project import ProjectInput, ProjectRead, ProjectsUploadResult
from app.services import profile_service
from app.utils.document_parser import SUPPORTED_EXTENSIONS

router = APIRouter()


async def _read_document(file: UploadFile) -> bytes:
    if file.size and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=messages.file_too_large(settings.max_upload_mb),
        )
    if not (file.filename or "").lower().endswith(SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=messages.DOCUMENT_REQUIRED,
        )
    return await file.read()


def _snapshot(
    candidate: Candidate, projects: list[Project], summary: str | None
) -> CVUploadResult:
    """Assemble the profile snapshot returned by both upload and read."""
    return CVUploadResult(
        profile=ProfileRead.model_validate(candidate),
        resume_summary=summary,
        projects=[ProjectRead.model_validate(p) for p in projects],
    )


@router.post("/cv", response_model=CVUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVUploadResult:
    data = await _read_document(file)
    try:
        profile, projects, summary = await profile_service.process_cv(
            db, current_user.user_id, file.filename or "cv.pdf", data
        )
    except DocumentParseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return _snapshot(profile, projects, summary)


@router.patch("", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    """Persist edited profile fields to the candidate and return the updated profile."""
    return await profile_service.update_candidate(
        db, current_user.user_id, payload.model_dump(exclude_unset=True)
    )


@router.get("", response_model=CVUploadResult)
async def read_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVUploadResult:
    """Return the onboarding snapshot: profile, active-resume summary, and CV projects."""
    snapshot = await profile_service.get_profile(db, current_user.user_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.PROFILE_NOT_FOUND
        )
    return _snapshot(*snapshot)


@router.put("/projects", response_model=list[ProjectRead])
async def replace_projects(
    projects: list[ProjectInput],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Project]:
    """Replace the user's entire project set (all sources) with the edited set."""
    return await profile_service.set_projects(db, current_user.user_id, projects)


@router.post(
    "/projects/upload",
    response_model=ProjectsUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_projects(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectsUploadResult:
    """Parse a projects PDF/DOCX with the LLM and replace the user's projects_pdf projects."""
    data = await _read_document(file)
    try:
        projects = await profile_service.process_projects_pdf(
            db, current_user.user_id, file.filename or "projects.pdf", data
        )
    except DocumentParseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return ProjectsUploadResult(projects=[ProjectRead.model_validate(p) for p in projects])
