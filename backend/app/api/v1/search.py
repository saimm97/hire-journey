import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResultsResponse, SearchRunResponse
from app.services import search_service

router = APIRouter()


@router.post("/run", response_model=SearchRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_search(
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchRunResponse:
    """Fetch jobs from all active ATS boards, filter, and score against the provided terms.

    Creates a search session and returns its id. Use GET /{session_id}/results
    to retrieve ranked results.
    """
    session, total = await search_service.run_search(
        db=db,
        user_id=current_user.user_id,
        resume_id=payload.resume_id,
        search_terms=payload.search_terms,
    )
    return SearchRunResponse(session_id=session.session_id, total_jobs_scored=total)


@router.get("/{session_id}/results", response_model=SearchResultsResponse)
async def get_results(
    session_id: str,
    min_score: int = Query(default=0, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResultsResponse:
    """Return ranked jobs for a session, filtered by minimum score."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid session_id")

    return await search_service.get_results(
        db=db,
        session_id=sid,
        user_id=current_user.user_id,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
