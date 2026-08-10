import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.sources.ashby import AshbySource
from app.sources.base import JobSource
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource
from app.sources.url_policy import validate_ats_url


@dataclass(frozen=True)
class SourceRegistration:
    """One adapter and the operational policy required to schedule it."""

    source: JobSource
    concurrency_limit: int


SOURCE_REGISTRY: dict[str, SourceRegistration] = {
    "greenhouse": SourceRegistration(GreenhouseSource(), concurrency_limit=6),
    "ashby": SourceRegistration(AshbySource(), concurrency_limit=4),
    "lever": SourceRegistration(LeverSource(), concurrency_limit=4),
}


def _build_host_index(attribute: str) -> dict[str, SourceRegistration]:
    index: dict[str, SourceRegistration] = {}
    for name, registration in SOURCE_REGISTRY.items():
        source = registration.source
        if source.name != name:
            raise RuntimeError(f"ATS registry key {name!r} does not match {source.name!r}")
        if registration.concurrency_limit < 1:
            raise RuntimeError(f"ATS provider {name!r} needs a positive concurrency limit")

        hosts = getattr(source, attribute)
        if not hosts:
            raise RuntimeError(f"ATS provider {name!r} must declare {attribute}")
        for host in hosts:
            normalized = host.lower()
            if not normalized or normalized != host or "/" in normalized:
                raise RuntimeError(f"ATS provider {name!r} declares an invalid host: {host!r}")
            previous = index.get(normalized)
            if previous is not None:
                raise RuntimeError(
                    f"ATS host {normalized!r} is claimed by both "
                    f"{previous.source.name!r} and {name!r}"
                )
            index[normalized] = registration
    return index


# Compatibility view used by parsing and description code. SOURCE_REGISTRY is
# the sole manually maintained registry; every other lookup is derived from it.
SOURCES: dict[str, JobSource] = {
    name: registration.source for name, registration in SOURCE_REGISTRY.items()
}
_HOST_INDEX = _build_host_index("hosts")
_FEED_HOST_INDEX = _build_host_index("feed_hosts")

_BOARD_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def supports_provider(provider: str) -> bool:
    """Return whether HireJourney has a registered parser for this ATS."""
    return provider.strip().lower() in SOURCES


def normalize_board_slug(board_slug: str) -> str:
    """Validate and normalize a board slug before it is used in a URL path."""
    slug = board_slug.strip()
    if not _BOARD_SLUG.fullmatch(slug):
        raise ValueError(f"Invalid ATS board slug: {board_slug!r}")
    return slug


def build_job_feed_url(provider: str, board_slug: str) -> str:
    """Build a supported ATS feed URL before a company is persisted.

    Keeping URL construction in the adapter registry gives YAML seeding and
    future admin/import paths one authoritative rule. Slugs are deliberately
    restricted because they are interpolated into provider URL paths.
    """
    provider_name = provider.strip().lower()
    source = SOURCES.get(provider_name)
    if source is None:
        raise ValueError(f"Unsupported ATS provider: {provider}")

    slug = normalize_board_slug(board_slug)
    return source.build_list_url(slug)


def source_for_url(url: str) -> JobSource | None:
    """Return the adapter that serves this posting URL, or None if unrecognised.

    Companies on a custom ATS domain won't match; callers should fall back to
    trying every adapter rather than treating None as "no source exists".
    """
    host = (urlparse(url).hostname or "").lower()
    registration = _HOST_INDEX.get(host)
    return registration.source if registration is not None else None


def registration_for_feed_url(url: str) -> SourceRegistration | None:
    """Resolve a safe feed URL to its adapter and scheduling policy."""
    try:
        parsed = validate_ats_url(url)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    return _FEED_HOST_INDEX.get(host)


def source_for_feed_url(url: str) -> JobSource | None:
    """Resolve a stored ATS feed URL to exactly one allowlisted adapter."""
    registration = registration_for_feed_url(url)
    return registration.source if registration is not None else None
