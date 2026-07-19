"""Profile onboarding request and response schemas.

The strict counterparts to app.schemas.extraction: these validate the
user-edited payloads, where rejecting bad input with a field-level 422 is
the correct behavior (unlike LLM output, which gets lenient normalization).
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.project import ProjectRead
from app.utils import normalization, patterns

WorkMode = Literal["remote", "hybrid", "onsite"]
SeniorityLevel = Literal[
    "intern",
    "entry_level",
    "associate",
    "mid_level",
    "senior",
    "lead",
    "manager",
    "director",
]


def _month_or_none(value: str | None) -> str | None:
    """Strictly validate a user-edited month string (YYYY-MM); blank clears."""
    if value is None or not value.strip():
        return None
    value = value.strip()
    if not patterns.STRICT_MONTH_RE.match(value):
        raise ValueError("must be in YYYY-MM format")
    return value


def _url_or_none(value: str | None) -> str | None:
    """Normalize a user-edited URL (https:// added to bare domains); blank clears."""
    if value is None or not value.strip():
        return None
    normalized = normalization.normalize_url(value)
    if normalized is None:
        raise ValueError("is not a valid URL")
    return normalized


def _clean_str_list(values: list[str]) -> list[str]:
    """Trim entries, drop blanks, dedupe case-insensitively keeping first casing."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = value.strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


# ── Read models ────────────────────────────────────────────────────────


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
    # Set from the authenticated User, never stored on the profile.
    account_email: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("technologies", mode="before")
    @classmethod
    def _technology_names(cls, value: object) -> object:
        """Accept ProfileTechnology rows (via their .name property) or plain strings."""
        if isinstance(value, (list, tuple)):
            return [item if isinstance(item, str) else item.name for item in value]
        return value


class ResumeMeta(BaseModel):
    """Source-resume metadata for the snapshot — never the raw text."""

    id: int
    file_name: str
    created_at: datetime
    summary: str | None


class EmploymentRead(BaseModel):
    id: int
    company_name: str
    title: str
    start_date: date | None
    end_date: date | None
    description: str | None


class OnboardingSnapshot(BaseModel):
    profile: ProfileRead
    source_resume: ResumeMeta | None
    employment_history: list[EmploymentRead]
    projects: list[ProjectRead]
    onboarding_complete: bool


# ── Details step (PUT /profile/details) ────────────────────────────────


class SocialLinksUpdate(BaseModel):
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    @field_validator("github_url", "linkedin_url", "portfolio_url")
    @classmethod
    def _urls(cls, value: str | None) -> str | None:
        return _url_or_none(value)


class EducationEntry(BaseModel):
    institution: str = Field(min_length=1, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    field: str | None = Field(default=None, max_length=255)
    start_date: str | None = None
    end_date: str | None = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _months(cls, value: str | None) -> str | None:
        return _month_or_none(value)


class CertificationEntry(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    issuer: str | None = Field(default=None, max_length=255)
    issued_at: str | None = None
    expires_at: str | None = None

    @field_validator("issued_at", "expires_at")
    @classmethod
    def _months(cls, value: str | None) -> str | None:
        return _month_or_none(value)


class EmploymentEntry(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _months(cls, value: str | None) -> str | None:
        return _month_or_none(value)

    @model_validator(mode="after")
    def _ordered(self) -> "EmploymentEntry":
        # Lexicographic compare is correct for zero-padded YYYY-MM strings.
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("employment end month cannot precede its start month")
        return self


class ProjectEntry(BaseModel):
    """A project in the details payload.

    project_id present -> edit of an existing project (must belong to this
    profile); absent -> a new project. Omitted projects are removed.
    """

    project_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    github_url: str | None = None
    deployed_url: str | None = None
    technologies: list[str] = Field(default_factory=list)

    @field_validator("github_url", "deployed_url")
    @classmethod
    def _urls(cls, value: str | None) -> str | None:
        return _url_or_none(value)

    @field_validator("technologies")
    @classmethod
    def _clean_technologies(cls, value: list[str]) -> list[str]:
        return _clean_str_list(value)


class ProfileDetailsUpdate(BaseModel):
    """The complete details step; collections are full replacements (PUT)."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    summary: str | None = None
    social_links: SocialLinksUpdate = Field(default_factory=SocialLinksUpdate)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    employment_history: list[EmploymentEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @field_validator("technologies")
    @classmethod
    def _clean_technologies(cls, value: list[str]) -> list[str]:
        return _clean_str_list(value)


# ── Preferences step (PUT /profile/preferences) ────────────────────────


class PreferencesUpdate(BaseModel):
    minimum_salary: int | None = Field(default=None, ge=0)
    desired_roles: list[str]
    desired_locations: list[str] = Field(default_factory=list)
    work_modes_preferred: list[WorkMode]
    seniority_level: SeniorityLevel

    @field_validator("desired_roles", "desired_locations")
    @classmethod
    def _clean_lists(cls, value: list[str]) -> list[str]:
        return _clean_str_list(value)

    @model_validator(mode="after")
    def _completion_requirements(self) -> "PreferencesUpdate":
        """This step's completion rules: cleaned lists must not end up empty."""
        if not self.desired_roles:
            raise ValueError("at least one desired role is required")
        if not self.work_modes_preferred:
            raise ValueError("at least one preferred work mode is required")
        # Dedupe while preserving order (Literal values are already valid).
        self.work_modes_preferred = list(dict.fromkeys(self.work_modes_preferred))
        return self


# ── Post-onboarding partial editing (PATCH /profile) ───────────────────


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
