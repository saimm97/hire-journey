"""Profile endpoints: build and persist the user's profile from uploads and edits."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import PdfNoTextError, PdfUnreadableError
from app.models.user import User
from app.schemas.profile import (
    ProfileRead,
    ProfileSnapshot,
    ProfileUpdate,
    ProjectsUploadResult,
)
from app.schemas.project import ProjectInput, ProjectRead
from app.services import pdf, profile_service

router = APIRouter()


async def _validate_pdf(file: UploadFile) -> bytes:
    if file.size and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=messages.file_too_large(settings.max_upload_mb),
        )
    data = await file.read()
    if not pdf.is_pdf(data):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=messages.PDF_REQUIRED,
        )
    return data


def _pdf_error_handler(exc: Exception) -> None:
    if isinstance(exc, PdfUnreadableError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=messages.PDF_UNREADABLE,
        )
    if isinstance(exc, PdfNoTextError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=messages.PDF_NO_TEXT,
        )
    raise exc


def _snapshot(candidate, summary, projects) -> ProfileSnapshot:
    return ProfileSnapshot(
        profile=ProfileRead.model_validate(candidate),
        resume_summary=summary,
        projects=[ProjectRead.model_validate(p) for p in projects],
    )


@router.get("", response_model=ProfileSnapshot)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileSnapshot:
    candidate, projects, summary = await profile_service.get_snapshot(db, current_user.user_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.PROFILE_NOT_FOUND
        )
    return _snapshot(candidate, summary, projects)


@router.patch("", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    candidate = await profile_service.update_profile(
        db, current_user.user_id, payload.model_dump(exclude_unset=True)
    )
    return ProfileRead.model_validate(candidate)


@router.post("/cv", response_model=ProfileSnapshot, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileSnapshot:
    data = await _validate_pdf(file)
    try:
        candidate, projects, summary = await profile_service.process_cv(
            db, current_user.user_id, file.filename or "cv.pdf", data
        )
        return _snapshot(candidate, summary, projects)
    except Exception as exc:
        _pdf_error_handler(exc)


@router.put("/projects", response_model=list[ProjectRead])
async def replace_projects(
    payload: list[ProjectInput],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectRead]:
    projects = await profile_service.set_projects(db, current_user.user_id, payload)
    return [ProjectRead.model_validate(p) for p in projects]


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
    data = await _validate_pdf(file)
    try:
        projects = await profile_service.process_projects_pdf(db, current_user.user_id, data)
        return ProjectsUploadResult(projects=[ProjectRead.model_validate(p) for p in projects])
    except Exception as exc:
        _pdf_error_handler(exc)
