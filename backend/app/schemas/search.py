from pydantic import BaseModel


class JobResult(BaseModel):
    job_id: int
    title: str
    company_name: str
    location: str | None
    url: str
    score: int


class SearchResultsResponse(BaseModel):
    total: int
    results: list[JobResult]
