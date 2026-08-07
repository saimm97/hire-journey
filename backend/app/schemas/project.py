"""Project schemas."""

from pydantic import BaseModel, Field


class ProjectRead(BaseModel):
    project_id: int
    name: str
    summary: str | None
    tech_stack: list[str] = Field(default_factory=list)
    github_url: str | None = None
    deployed_url: str | None = None
