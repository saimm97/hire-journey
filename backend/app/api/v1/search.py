from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.search import SearchResultsResponse, SearchRunResponse
from app.services import search_service
from app.services.ingestion_report import RunStatus

router = APIRouter()


@router.post("/run", response_model=SearchRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_scan(
    _: User = Depends(get_current_user),
) -> SearchRunResponse:
    """Fetch every configured ATS feed once and idempotently store its public jobs.

    Scores are not persisted — rank stored jobs with GET /results.
    """
    report = await search_service.run_scan_locked()
    if report.status is RunStatus.SKIPPED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A job-ingestion run is already active.",
        )
    return SearchRunResponse(total_jobs_fetched=report.jobs_upserted)


@router.get("/results", response_model=SearchResultsResponse)
async def get_results(
    terms: list[str] | None = Query(
        default=None,
        description="Optional keyword override; defaults to the caller's desired roles",
    ),
    min_score: int = Query(default=0, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResultsResponse:
    """Rank stored jobs against the caller's profile (roles + technologies).

    Pass `terms` to override the roles with an explicit search.
    """
    return await search_service.get_results(
        db=db,
        user_id=current_user.id,
        search_terms=terms,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
