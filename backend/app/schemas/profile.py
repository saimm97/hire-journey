"""Profile schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.project import ParsedProject, ProjectRead


class ExperienceItem(BaseModel):
    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    highlights: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ResumeExtraction(BaseModel):
    """Structured resume data the LLM must return for an uploaded document."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    projects: list[ParsedProject] = Field(default_factory=list)

    @field_validator("email", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        return value or None


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


class ProfileUpdate(BaseModel):
    """User-editable candidate fields; keys left unset are unchanged on PATCH."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    tech_stack: list[str] | None = None
    desired_role: list[str] | None = None
    minimum_salary: int | None = Field(default=None, ge=0)

    @field_validator("email", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        """Treat an empty email string as an explicit clear."""
        return value or None

    @field_validator("desired_role")
    @classmethod
    def _null_roles_to_empty(cls, value: list[str] | None) -> list[str]:
        """Coerce an explicit null to an empty list; the column is non-nullable."""
        return value if value is not None else []


class CVUploadResult(BaseModel):
    profile: ProfileRead
    resume_summary: str | None
    projects: list[ProjectRead]
