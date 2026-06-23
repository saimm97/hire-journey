import uuid
from datetime import datetime

from pydantic import BaseModel


class EvaluationRequest(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID


class EvaluationResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    match_score: int
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
