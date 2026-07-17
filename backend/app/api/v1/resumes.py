from fastapi import APIRouter, Depends
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
    """List the caller's resumes, newest (the one in use) first."""
    resumes = await resume_service.list_resumes(db, current_user.id)
    return [ResumeRead.model_validate(resume) for resume in resumes]
