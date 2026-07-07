"""Project schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ParsedProject(BaseModel):
    """A project parsed from a document, before it is persisted."""

    name: str
    summary: str | None = Field(
        default=None,
        description="The project's full description, copied verbatim from the resume — not summarized.",
    )
    tech_stack: list[str] = []
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
    source: str
