"""Project schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ParsedProject(BaseModel):
    """A project parsed from a document, before it is persisted."""

    name: str
    summary: str | None = Field(
        default=None,
        description=(
            "The project's full description, copied verbatim from the resume — "
            "not summarized."
        ),
    )
    tech_stack: list[str] = []
    github_url: str | None = None
    deployed_url: str | None = None


class ProjectInput(ParsedProject):
    """An edited project sent back to replace the stored set.

    Carries its own ``source`` (``"cv"`` / ``"projects_pdf"``) so the full-set
    replacement keeps each project's origin.
    """

    source: str = "cv"


class ProjectsExtraction(BaseModel):
    """The structured projects the LLM must return for an uploaded projects document."""

    projects: list[ParsedProject] = Field(default_factory=list)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    name: str
    summary: str | None
    tech_stack: list[str] | None
    github_url: str | None
    deployed_url: str | None
    source: str


class ProjectsUploadResult(BaseModel):
    projects: list[ProjectRead]
