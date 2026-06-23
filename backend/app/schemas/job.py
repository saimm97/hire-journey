import uuid

from pydantic import BaseModel


class JobDetail(BaseModel):
    job_id: uuid.UUID
    title: str
    company_name: str
    location: str | None
    url: str
    description: str | None
    salary_min: int | None
    salary_max: int | None
    source_name: str

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    total: int
    results: list[JobDetail]
