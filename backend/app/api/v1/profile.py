"""Profile endpoints: build the user's profile from uploaded documents."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import PdfNoTextError, PdfUnreadableError
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import (
    CVUploadResult,
    LinkedInUploadResult,
    ProfileRead,
    ProfileUpdate,
    ProjectsUploadResult,
)
from app.services import pdf, profile_service, resume_service

router = APIRouter()


@router.get("", response_model=CVUploadResult)
async def read_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVUploadResult:
    snapshot = await profile_service.get_profile(db, current_user.id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile has not been created yet.",
        )
    profile, projects, resume_summary = snapshot
    return CVUploadResult(
        profile=ProfileRead.model_validate(profile),
        resume_summary=resume_summary,
        projects=projects,
    )


@router.patch("", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    return await profile_service.update_profile(
        db,
        current_user.id,
        payload.model_dump(exclude_unset=True),
    )


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


@router.post("/cv", response_model=CVUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    replace_resume_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVUploadResult:
    data = await _validate_pdf(file)
    try:
        profile, projects, summary = await profile_service.process_cv(
            db,
            current_user.id,
            file.filename or "cv.pdf",
            data,
            replace_resume_id=replace_resume_id,
        )
        return CVUploadResult(
            profile=ProfileRead.model_validate(profile),
            resume_summary=summary,
            projects=projects,
        )
    except Exception as exc:
        if isinstance(exc, resume_service.ResumeLimitError):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if isinstance(exc, resume_service.ResumeNotFoundError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        _pdf_error_handler(exc)


@router.post("/linkedin", response_model=LinkedInUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_linkedin(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinkedInUploadResult:
    data = await _validate_pdf(file)
    try:
        profile = await profile_service.process_linkedin(db, current_user.id, data)
        return LinkedInUploadResult(profile=ProfileRead.model_validate(profile))
    except Exception as exc:
        _pdf_error_handler(exc)


@router.post("/projects", response_model=ProjectsUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_projects(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectsUploadResult:
    data = await _validate_pdf(file)
    try:
        projects = await profile_service.process_projects_pdf(db, current_user.id, data)
        return ProjectsUploadResult(projects=projects)
    except Exception as exc:
        _pdf_error_handler(exc)
