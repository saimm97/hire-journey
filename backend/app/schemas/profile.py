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


class LinkedInExtraction(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    tech_stack: list[str] = []
    linkedin_summary: str | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    first_name: str | None
    last_name: str | None
    email: EmailStr | None
    phone: str | None
    github_url: str | None
    portfolio_url: str | None
    minimum_salary: int | None
    tech_stack: list[str] | None
    desired_role: list[str]
    linkedin_data: dict | None
    source_resume_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CVUploadResult(BaseModel):
    profile: ProfileRead
    resume_summary: str | None
    projects: list[ProjectRead]


class LinkedInUploadResult(BaseModel):
    profile: ProfileRead


class ProjectsUploadResult(BaseModel):
    projects: list[ProjectRead]
