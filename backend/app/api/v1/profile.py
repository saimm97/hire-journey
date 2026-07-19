"""Profile endpoints: resume upload, onboarding steps, and the snapshot read."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.exceptions import (
    DocumentParseError,
    ExtractionError,
    LLMNotConfiguredError,
    ProfileNotFoundError,
    ProjectOwnershipError,
)
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import (
    OnboardingSnapshot,
    PreferencesUpdate,
    ProfileDetailsUpdate,
    ProfileRead,
    ProfileUpdate,
)
from app.services import profile_service, resume_service
from app.utils import document_parser

router = APIRouter()


async def _snapshot(db: AsyncSession, user: User) -> OnboardingSnapshot:
    pieces = await profile_service.get_snapshot(db, user.id)
    if pieces is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.PROFILE_NOT_FOUND
        )
    profile, source_resume, employments, projects = pieces
    profile_read = ProfileRead.model_validate(profile).model_copy(
        update={"account_email": user.email}
    )
    return OnboardingSnapshot(
        profile=profile_read,
        source_resume=source_resume,
        employment_history=employments,
        projects=projects,
        onboarding_complete=profile_service.is_onboarding_complete(profile),
    )


@router.get("", response_model=OnboardingSnapshot)
async def read_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingSnapshot:
    return await _snapshot(db, current_user)


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


@router.post("/cv", response_model=OnboardingSnapshot, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    replace_resume_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingSnapshot:
    _validate_upload(file)
    data = await file.read()
    try:
        await profile_service.process_cv(
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
    return await _snapshot(db, current_user)


@router.put("/details", response_model=OnboardingSnapshot)
async def save_details(
    payload: ProfileDetailsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingSnapshot:
    try:
        await profile_service.save_details(db, current_user.id, payload)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProjectOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return await _snapshot(db, current_user)


@router.put("/preferences", response_model=OnboardingSnapshot)
async def save_preferences(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingSnapshot:
    try:
        await profile_service.save_preferences(db, current_user.id, payload)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return await _snapshot(db, current_user)
