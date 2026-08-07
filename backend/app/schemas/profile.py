"""Profile onboarding request and response schemas.

The strict counterparts to app.schemas.extraction: these validate the
user-edited payloads, where rejecting bad input with a field-level 422 is
the correct behavior (unlike LLM output, which gets lenient normalization).
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

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
    if not 1900 <= int(value[:4]) <= 2100:
        raise ValueError("year must be between 1900 and 2100")
    return value


def _year_or_month_or_none(value: str | None) -> str | None:
    """Validate a year-only (YYYY) or full-month (YYYY-MM) string; blank clears.

    Education and certification dates keep whatever precision the resume gave —
    a bare year stays a year rather than being padded to a month we never saw.
    """
    if value is None or not value.strip():
        return None
    value = value.strip()
    if not patterns.STRICT_YEAR_OR_MONTH_RE.match(value):
        raise ValueError("must be in YYYY or YYYY-MM format")
    if not 1900 <= int(value[:4]) <= 2100:
        raise ValueError("year must be between 1900 and 2100")
    return value


def _unambiguously_precedes(start: str | None, end: str | None) -> bool:
    """Whether an end date is definitely earlier than its start date.

    A year-only value has intentionally unknown month precision. Within the
    same year, only reject when both sides include months and those months are
    reversed. Different years are always comparable.
    """
    if not start or not end:
        return False
    start_year, end_year = int(start[:4]), int(end[:4])
    if end_year != start_year:
        return end_year < start_year
    if len(start) == 7 and len(end) == 7:
        return end < start
    return False


def _url_or_none(value: str | None) -> str | None:
    """Normalize a user-edited URL (https:// added to bare domains); blank clears."""
    if value is None or not value.strip():
        return None
    normalized = normalization.normalize_url(value)
    if normalized is None:
        raise ValueError("is not a valid URL")
    if len(normalized) > 255:
        raise ValueError("is too long (255 characters max)")
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


class CompletionIssue(BaseModel):
    """One unmet onboarding requirement, including the step that owns it."""

    step: Literal["profile", "preferences"]
    path: list[str | int]
    message: str


class OnboardingSnapshot(BaseModel):
    profile: ProfileRead
    source_resume: ResumeMeta | None
    employment_history: list[EmploymentRead]
    projects: list[ProjectRead]
    onboarding_complete: bool
    completion_issues: list[CompletionIssue]


class StrictRequest(BaseModel):
    """Base for user-edited payloads: an unknown key is a 422, never a shrug.

    Every collection below is a full replacement, so a silently dropped key
    doesn't merely fail to apply — it clears the stored value.
    """

    model_config = ConfigDict(extra="forbid")


class SocialLinksUpdate(StrictRequest):
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    @field_validator("github_url", "linkedin_url", "portfolio_url")
    @classmethod
    def _urls(cls, value: str | None) -> str | None:
        return _url_or_none(value)


class EducationEntry(StrictRequest):
    institution: str = Field(min_length=1, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    field: str | None = Field(default=None, max_length=255)
    start_date: str | None = None
    end_date: str | None = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _months(cls, value: str | None) -> str | None:
        return _year_or_month_or_none(value)

    @field_validator("end_date")
    @classmethod
    def _ordered(cls, value: str | None, info: ValidationInfo) -> str | None:
        if _unambiguously_precedes(info.data.get("start_date"), value):
            raise ValueError("education end date cannot precede its start date")
        return value


class CertificationEntry(StrictRequest):
    name: str = Field(min_length=1, max_length=255)
    issuer: str | None = Field(default=None, max_length=255)
    issued_at: str | None = None
    expires_at: str | None = None

    @field_validator("issued_at", "expires_at")
    @classmethod
    def _months(cls, value: str | None) -> str | None:
        return _year_or_month_or_none(value)

    @field_validator("expires_at")
    @classmethod
    def _ordered(cls, value: str | None, info: ValidationInfo) -> str | None:
        if _unambiguously_precedes(info.data.get("issued_at"), value):
            raise ValueError("expiration date cannot precede its issue date")
        return value


class EmploymentEntry(StrictRequest):
    company_name: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _months(cls, value: str | None) -> str | None:
        return _month_or_none(value)

    @field_validator("end_date")
    @classmethod
    def _ordered(cls, value: str | None, info: ValidationInfo) -> str | None:
        if _unambiguously_precedes(info.data.get("start_date"), value):
            raise ValueError("employment end month cannot precede its start month")
        return value


class ProjectEntry(StrictRequest):
    """A project in the details payload.

    project_id present -> edit of an existing project (must belong to this
    profile); absent -> a new project. Omitted projects are removed.
    """

    project_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    github_url: str | None = None
    deployed_url: str | None = None
    technologies: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("github_url", "deployed_url")
    @classmethod
    def _urls(cls, value: str | None) -> str | None:
        return _url_or_none(value)

    @field_validator("technologies")
    @classmethod
    def _clean_technologies(cls, value: list[str]) -> list[str]:
        return _clean_str_list(value)


class ProfileDetailsUpdate(StrictRequest):
    """The complete details step; collections are full replacements (PATCH)."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    summary: str | None = None
    social_links: SocialLinksUpdate = Field(default_factory=SocialLinksUpdate)
    education: list[EducationEntry] = Field(default_factory=list, max_length=100)
    certifications: list[CertificationEntry] = Field(default_factory=list, max_length=100)
    employment_history: list[EmploymentEntry] = Field(default_factory=list, max_length=100)
    projects: list[ProjectEntry] = Field(default_factory=list, max_length=100)
    technologies: list[str] = Field(default_factory=list, max_length=300)

    @field_validator("technologies")
    @classmethod
    def _clean_technologies(cls, value: list[str]) -> list[str]:
        return _clean_str_list(value)


# ── Preferences section (PATCH /profile) ───────────────────────────────


class PreferencesUpdate(StrictRequest):
    # Upper bound keeps the value safely inside the INTEGER column (int32).
    minimum_salary: int | None = Field(default=None, ge=0, le=100_000_000)
    desired_roles: list[str] = Field(max_length=100)
    desired_locations: list[str] = Field(max_length=100)
    work_modes_preferred: list[WorkMode]
    seniority_level: SeniorityLevel

    @field_validator("desired_locations")
    @classmethod
    def _require_locations(cls, value: list[str]) -> list[str]:
        cleaned = _clean_str_list(value)
        if not cleaned:
            raise ValueError("Add at least one desired location.")
        return cleaned

    # Field-level (not model-level) so the required-empty errors carry a concrete
    # loc — ['body', 'desired_roles'] — the frontend can map to the right control.
    # A model_validator would report an empty loc the client cannot address.
    @field_validator("desired_roles")
    @classmethod
    def _require_roles(cls, value: list[str]) -> list[str]:
        cleaned = _clean_str_list(value)
        if not cleaned:
            raise ValueError("Add at least one desired role.")
        return cleaned

    @field_validator("work_modes_preferred")
    @classmethod
    def _require_work_modes(cls, value: list[WorkMode]) -> list[WorkMode]:
        # Dedupe while preserving order (Literal values are already valid).
        deduped = list(dict.fromkeys(value))
        if not deduped:
            raise ValueError("Pick at least one work mode.")
        return deduped


# ── Post-onboarding partial editing (PATCH /profile) ───────────────────


class ProfileUpdate(StrictRequest):
    """Editable onboarding fields; omitted keys remain unchanged on PATCH."""

    details: ProfileDetailsUpdate | None = None
    preferences: PreferencesUpdate | None = None

    @model_validator(mode="after")
    def require_section(self) -> "ProfileUpdate":
        if self.details is None and self.preferences is None:
            raise ValueError("Provide details or preferences.")
        return self
