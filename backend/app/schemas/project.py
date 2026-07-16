"""Project schemas."""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ParsedProject(BaseModel):
    """A project parsed from a document, before it is persisted."""

    name: str
    summary: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    github_url: str | None = None
    deployed_url: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    name: str
    summary: str | None
    tech_stack: list[str] | None
    github_url: str | None
    deployed_url: str | None
    project_start_date: date | None = None
    project_end_date: date | None = None
    role: str | None = None
    contribution_summary: str | None = None
    participation_start_date: date | None = None
    participation_end_date: date | None = None
    is_current: bool = False
    source: str | None = None
