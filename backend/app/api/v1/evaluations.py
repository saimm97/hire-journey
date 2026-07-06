import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.exceptions import ExtractionError
from app.models.evaluation import Evaluation
from app.models.user import User
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.services import evaluation_service

router = APIRouter()


@router.post("", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationResponse:
    """Run LLM deep evaluation for a job against the given resume.

    Returns existing evaluation if one already exists for this (job, resume) pair.
    """
    try:
        evaluation = await evaluation_service.run_evaluation(
            db=db,
            user_id=current_user.user_id,
            job_id=payload.job_id,
            resume_id=payload.resume_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    return EvaluationResponse.model_validate(evaluation)


@router.get("/{job_id}", response_model=EvaluationResponse)
async def get_evaluation(
    job_id: uuid.UUID,
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationResponse:
    """Return the most recent evaluation for a job + resume pair."""
    row = (
        await db.execute(
            select(Evaluation)
            .where(
                Evaluation.job_id == job_id,
                Evaluation.user_id == current_user.user_id,
                Evaluation.resume_id == resume_id,
            )
            .order_by(Evaluation.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation found for this job and resume",
        )

    return EvaluationResponse.model_validate(row)
