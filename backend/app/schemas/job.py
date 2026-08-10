from datetime import datetime

from pydantic import BaseModel


class JobDetail(BaseModel):
    id: int
    title: str
    company_name: str
    location: str | None
    url: str
    description: str | None
    salary_min: int | None
    salary_max: int | None
    deadline: datetime | None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    total: int
    results: list[JobDetail]
