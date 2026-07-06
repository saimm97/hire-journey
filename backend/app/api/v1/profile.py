"""Profile endpoint: build the user's profile from an uploaded resume document."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import DocumentParseError, ExtractionError
from app.models.user import User
from app.schemas.profile import CVUploadResult, ProfileRead
from app.schemas.project import ProjectRead
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

    return CVUploadResult(
        profile=ProfileRead.model_validate(profile),
        resume_summary=summary,
        projects=[ProjectRead.model_validate(p) for p in projects],
    )
