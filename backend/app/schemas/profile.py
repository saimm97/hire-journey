"""Profile schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.project import ProjectRead


class CVExtraction(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
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
    email: EmailStr | None
    phone: str | None
    github_url: str | None
    portfolio_url: str | None
    summary: str | None
    minimum_salary: int | None
    tech_stack: list[str] | None
    desired_role: list[str]
    seniority_level: list[str]
    location: list[str]
    work_mode: str | None
    open_to_relocating: bool
    source_resume_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    """Partial candidate update: only the fields sent are persisted (exclude_unset).

    Covers identity, skills, summary, and every job preference (roles, salary,
    location, work mode, relocating), so one PATCH backs both onboarding steps.
    """

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    summary: str | None = None
    tech_stack: list[str] | None = None
    desired_role: list[str] | None = None
    seniority_level: list[str] | None = None
    minimum_salary: int | None = None
    location: list[str] | None = None
    work_mode: str | None = None
    open_to_relocating: bool | None = None


class ProfileSnapshot(BaseModel):
    """The full onboarding state: the profile plus its resume summary and projects.

    Returned by GET /profile (persistence load) and POST /profile/cv (after parsing).
    """

    profile: ProfileRead
    resume_summary: str | None
    projects: list[ProjectRead]


class ProjectsUploadResult(BaseModel):
    projects: list[ProjectRead]
