"""Profile onboarding request, extraction, and response schemas."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.project import ProjectRead


class CVExtraction(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    summary: str | None = None


class LinkedInExtraction(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    linkedin_summary: str | None = None


class TechnologySelection(BaseModel):
    technology_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    proficiency: str | None = Field(default=None, max_length=30)
    years_experience: Decimal | None = Field(default=None, ge=0, max_digits=4, decimal_places=1)

    @model_validator(mode="after")
    def require_identifier(self) -> "TechnologySelection":
        if self.technology_id is None and not self.name:
            raise ValueError("technology_id or name is required")
        return self


class ProfileTechnologyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    technology_id: uuid.UUID
    canonical_name: str
    proficiency: str | None
    years_experience: Decimal | None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: uuid.UUID
    user_id: uuid.UUID
    first_name: str | None
    last_name: str | None
    phone_number: str | None
    location: str | None
    social_links: dict[str, str]
    education: list[dict[str, Any]]
    certifications: list[dict[str, Any]]
    title: str | None
    summary: str | None
    minimum_salary: int | None
    salary_currency: str | None
    salary_period: str | None
    desired_locations: list[str]
    desired_roles: list[str]
    work_modes_preferred: list[str]
    seniority_level: str | None
    technologies: list[ProfileTechnologyRead]
    source_resume_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    """Editable onboarding fields; omitted keys remain unchanged on PATCH."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    social_links: dict[str, str] | None = None
    education: list[dict[str, Any]] | None = None
    certifications: list[dict[str, Any]] | None = None
    title: str | None = Field(default=None, max_length=255)
    summary: str | None = None
    minimum_salary: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_period: str | None = Field(default=None, max_length=20)
    desired_locations: list[str] | None = None
    desired_roles: list[str] | None = None
    work_modes_preferred: list[str] | None = None
    seniority_level: str | None = Field(default=None, max_length=50)
    technologies: list[TechnologySelection] | None = None

    @field_validator("desired_locations", "desired_roles", "work_modes_preferred")
    @classmethod
    def null_array_to_empty(cls, value: list[str] | None) -> list[str]:
        return value if value is not None else []

    @field_validator("social_links")
    @classmethod
    def validate_social_links(cls, value: dict[str, str] | None) -> dict[str, str]:
        return value if value is not None else {}

    @field_validator("salary_currency")
    @classmethod
    def uppercase_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class CVUploadResult(BaseModel):
    profile: ProfileRead
    resume_summary: str | None
    projects: list[ProjectRead]


class LinkedInUploadResult(BaseModel):
    profile: ProfileRead


class ProjectsUploadResult(BaseModel):
    projects: list[ProjectRead]
