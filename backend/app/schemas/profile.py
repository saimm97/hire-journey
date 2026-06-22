"""Profile schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.project import ProjectRead


class CVExtraction(BaseModel):
    """Flat identity fields parsed from a CV. The professional summary is stored
    with the resume, not the profile."""

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    tech_stack: list[str] = []
    summary: str | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    linkedin_url: str | None
    github_url: str | None
    tech_stack: list[str] | None
    linkedin_summary: str | None
    source_resume_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CVUploadResult(BaseModel):
    """What the CV endpoint returns: the three destinations of one upload."""

    profile: ProfileRead
    resume_summary: str | None
    projects: list[ProjectRead]
