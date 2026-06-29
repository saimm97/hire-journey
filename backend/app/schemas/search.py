import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    search_terms: list[str] = Field(min_length=1, description="Keywords to score jobs against")
    resume_id: uuid.UUID


class JobResult(BaseModel):
    job_id: uuid.UUID
    title: str
    company_name: str
    location: str | None
    url: str
    score: int


class SearchRunResponse(BaseModel):
    session_id: uuid.UUID
    total_jobs_scored: int


class SearchResultsResponse(BaseModel):
    session_id: uuid.UUID
    total: int
    results: list[JobResult]
