from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.search import SearchResultsResponse, SearchRunResponse
from app.services import search_service

router = APIRouter()


@router.post("/run", response_model=SearchRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_scan(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SearchRunResponse:
    """Fetch jobs from every scannable company (all ATS boards tried) and store them.

    Scores are not persisted — rank stored jobs with GET /results.
    """
    total = await search_service.run_scan(db)
    return SearchRunResponse(total_jobs_fetched=total)


@router.get("/results", response_model=SearchResultsResponse)
async def get_results(
    terms: list[str] = Query(min_length=1, description="Keywords to score jobs against"),
    min_score: int = Query(default=0, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResultsResponse:
    """Rank stored jobs against the terms plus the caller's latest resume skills."""
    return await search_service.get_results(
        db=db,
        user_id=current_user.id,
        search_terms=terms,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
