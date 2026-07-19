"""Profile onboarding request and response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.project import ProjectRead


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
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
    desired_locations: list[str]
    desired_roles: list[str]
    work_modes_preferred: list[str]
    seniority_level: str | None
    technologies: list[str]
    source_resume_id: int | None
    created_at: datetime
    updated_at: datetime

    @field_validator("technologies", mode="before")
    @classmethod
    def _technology_names(cls, value: object) -> object:
        """Accept ProfileTechnology rows (via their .name property) or plain strings."""
        if isinstance(value, (list, tuple)):
            return [item if isinstance(item, str) else item.name for item in value]
        return value


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
    desired_locations: list[str] | None = None
    desired_roles: list[str] | None = None
    work_modes_preferred: list[str] | None = None
    seniority_level: str | None = Field(default=None, max_length=50)
    technologies: list[str] | None = None

    @field_validator("desired_locations", "desired_roles", "work_modes_preferred")
    @classmethod
    def null_array_to_empty(cls, value: list[str] | None) -> list[str]:
        return value if value is not None else []

    @field_validator("social_links")
    @classmethod
    def validate_social_links(cls, value: dict[str, str] | None) -> dict[str, str]:
        return value if value is not None else {}

class CVUploadResult(BaseModel):
    profile: ProfileRead
    resume_summary: str | None
    projects: list[ProjectRead]
