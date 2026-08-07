"""Lenient schemas for LLM resume extraction.

Deliberately loose — every field optional, plain strings, no format
constraints — because any constraint here becomes a retry trigger (and
ultimately a 502) on a perfectly good resume. Normalization (dates, URLs)
and requiredness are applied afterwards in our own code; the strict rules
live on the user-edited payload schemas instead.
"""

from pydantic import BaseModel, Field


class EmploymentItem(BaseModel):
    company_name: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class EducationItem(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class CertificationItem(BaseModel):
    name: str | None = None
    issuer: str | None = None
    issued_at: str | None = None
    expires_at: str | None = None


class ProjectItem(BaseModel):
    name: str | None = None
    summary: str | None = None
    github_url: str | None = None
    deployed_url: str | None = None
    technologies: list[str] = Field(default_factory=list)


class ResumeExtraction(BaseModel):
    """Structured resume data the LLM must return for an uploaded document."""

    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    location: str | None = None
    title: str | None = None
    summary: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    technologies: list[str] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    employment_history: list[EmploymentItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
