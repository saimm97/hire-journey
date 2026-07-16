import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.resume import ResumeRead
from app.services import resume_service

router = APIRouter()


@router.get("", response_model=list[ResumeRead])
async def read_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeRead]:
    resumes = await resume_service.list_resumes(db, current_user.user_id)
    return [ResumeRead.model_validate(resume) for resume in resumes]


@router.patch("/{resume_id}/active", response_model=ResumeRead)
async def set_active_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeRead:
    try:
        resume = await resume_service.activate_resume(db, current_user.user_id, resume_id)
    except resume_service.ResumeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResumeRead.model_validate(resume)
