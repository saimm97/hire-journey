import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.company import Company
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobDetail, JobListResponse
from app.services.job_service import get_job_with_description

router = APIRouter()


def _to_detail(job: Job) -> JobDetail:
    return JobDetail(
        job_id=job.job_id,
        title=job.title,
        company_name=job.company.name,
        location=job.location,
        url=job.url,
        description=job.description,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        source_name=job.source.name,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    company: str | None = Query(default=None, description="Filter by company name (substring)"),
    title: str | None = Query(default=None, description="Filter by title keyword (substring)"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> JobListResponse:
    """List all fetched jobs with optional company/title filters."""
    base = select(Job).options(selectinload(Job.company), selectinload(Job.source))

    if company:
        base = base.join(Job.company).where(Company.name.ilike(f"%{company}%"))
    if title:
        base = base.where(Job.title.ilike(f"%{title}%"))

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    rows = (
        await db.execute(base.order_by(Job.title).limit(limit).offset(offset))
    ).scalars().all()

    return JobListResponse(total=total, results=[_to_detail(j) for j in rows])


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> JobDetail:
    """Return a single job. Fetches Greenhouse description on demand if missing."""
    job = await get_job_with_description(db, job_id)

    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return _to_detail(job)
