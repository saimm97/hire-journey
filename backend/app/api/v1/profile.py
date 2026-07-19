"""Profile endpoints: build the user's profile from an uploaded resume."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import DocumentParseError, ExtractionError, LLMNotConfiguredError
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import CVUploadResult, ProfileRead, ProfileUpdate
from app.services import profile_service, resume_service
from app.utils import document_parser

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


def _validate_upload(file: UploadFile) -> None:
    if not document_parser.is_supported(file.filename or ""):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=messages.DOCUMENT_UNSUPPORTED,
        )
    if file.size and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=messages.file_too_large(settings.max_upload_mb),
        )


@router.post("/cv", response_model=CVUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    replace_resume_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVUploadResult:
    _validate_upload(file)
    data = await file.read()
    try:
        profile, projects, summary = await profile_service.process_cv(
            db,
            current_user.id,
            file.filename or "cv.pdf",
            data,
            replace_resume_id=replace_resume_id,
        )
    except resume_service.ResumeLimitError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except resume_service.ResumeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except LLMNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return CVUploadResult(
        profile=ProfileRead.model_validate(profile),
        resume_summary=summary,
        projects=projects,
    )
