"""Profile endpoints: build the user's profile from an uploaded CV."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.profile import CVUploadResult, ProfileRead
from app.schemas.project import ProjectRead
from app.services import pdf, profile_service

router = APIRouter()


@router.post("/cv", response_model=CVUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVUploadResult:
    """Upload a CV PDF, extract it, and return the profile, projects, and summary."""
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

    try:
        profile, projects, summary = await profile_service.process_cv(
            db, current_user.user_id, file.filename or "cv.pdf", data
        )
        return CVUploadResult(
            profile=ProfileRead.model_validate(profile),
            resume_summary=summary,
            projects=[ProjectRead.model_validate(project) for project in projects],
        )
    except pdf.PdfUnreadableError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=messages.PDF_UNREADABLE,
        )
    except pdf.PdfNoTextError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=messages.PDF_NO_TEXT,
        )
