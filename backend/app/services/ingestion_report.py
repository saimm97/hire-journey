"""Ephemeral operational report types for one ATS ingestion run."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID


class RunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProviderIngestionHealth(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class IssueStage(StrEnum):
    ROUTING = "routing"
    FETCH = "fetch"
    PARSE = "parse"
    PERSISTENCE = "persistence"
    RUN = "run"


class IssueCode(StrEnum):
    INVALID_FEED_URL = "invalid_feed_url"
    REQUEST_TIMEOUT = "request_timeout"
    CONNECTION_FAILED = "connection_failed"
    RATE_LIMITED = "rate_limited"
    PROVIDER_HTTP_ERROR = "provider_http_error"
    RESPONSE_TOO_LARGE = "response_too_large"
    INVALID_JSON = "invalid_json"
    INVALID_FEED = "invalid_feed"
    PERSISTENCE_FAILED = "persistence_failed"
    UNEXPECTED_FETCH_ERROR = "unexpected_fetch_error"
    UNEXPECTED_RUN_ERROR = "unexpected_run_error"
    EMPTY_FEED = "empty_feed"


def sanitize_feed_url(configured_url: str | None) -> str | None:
    """Remove URL components that must never enter reports or logs."""
    if not configured_url:
        return None
    try:
        parsed = urlsplit(configured_url.strip())
        if not parsed.scheme or not parsed.hostname:
            return None
        hostname = parsed.hostname
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"
        port = parsed.port
    except (TypeError, ValueError):
        return None

    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path, "", ""))


@dataclass(frozen=True)
class IngestionIssue:
    stage: IssueStage
    code: IssueCode
    message: str
    company_id: int | None = None
    company_name: str | None = None
    provider: str | None = None
    feed_url: str | None = None
    exception_type: str | None = None
    http_status: int | None = None
    retry_eligible: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "feed_url", sanitize_feed_url(self.feed_url))


@dataclass
class ProviderRunSummary:
    provider: str
    ingestion_health: ProviderIngestionHealth = ProviderIngestionHealth.HEALTHY
    feeds_attempted: int = 0
    feeds_succeeded: int = 0
    feeds_failed: int = 0
    empty_feeds: int = 0
    persistence_failures: int = 0
    jobs_fetched: int = 0
    jobs_upserted: int = 0


@dataclass
class IngestionRunReport:
    run_id: UUID
    status: RunStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    companies_attempted: int = 0
    companies_succeeded: int = 0
    companies_failed: int = 0
    empty_feeds: int = 0
    jobs_fetched: int = 0
    jobs_upserted: int = 0
    providers: list[ProviderRunSummary] = field(default_factory=list)
    warnings: list[IngestionIssue] = field(default_factory=list)
    errors: list[IngestionIssue] = field(default_factory=list)


class IngestionRunFailedError(RuntimeError):
    """A fatal ingestion failure whose safe operator report is still available."""

    def __init__(self, report: IngestionRunReport) -> None:
        super().__init__("Job ingestion failed before the run could complete")
        self.report = report


def _json_value(value):
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def report_to_dict(report: IngestionRunReport) -> dict:
    """Return the complete report as JSON-safe primitives."""
    return _json_value(asdict(report))
