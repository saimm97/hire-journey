from datetime import datetime

from pydantic import BaseModel


class EvaluationRequest(BaseModel):
    job_id: int


class EvaluationResponse(BaseModel):
    id: int
    job_id: int
    profile_id: int
    match_score: int
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
