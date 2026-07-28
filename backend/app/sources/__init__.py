import re
from urllib.parse import urlparse

from app.sources.ashby import AshbySource
from app.sources.base import JobSource
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource

SOURCES: dict[str, JobSource] = {
    "greenhouse": GreenhouseSource(),
    "ashby": AshbySource(),
    "lever": LeverSource(),
}

# host -> adapter, derived from each adapter's declared hosts. Registering a new
# adapter in SOURCES wires up its hosts automatically.
_HOST_INDEX: dict[str, JobSource] = {
    host: source for source in SOURCES.values() for host in source.hosts
}
_FEED_HOST_INDEX: dict[str, JobSource] = {
    host: source for source in SOURCES.values() for host in source.feed_hosts
}

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
    return _HOST_INDEX.get(host)


def source_for_feed_url(url: str) -> JobSource | None:
    """Resolve a stored ATS feed URL to exactly one allowlisted adapter."""
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() != "https"
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        return None
    return _FEED_HOST_INDEX.get(host)
