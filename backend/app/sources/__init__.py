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


def source_for_url(url: str) -> JobSource | None:
    """Return the adapter that serves this posting URL, or None if unrecognised.

    Companies on a custom ATS domain won't match; callers should fall back to
    trying every adapter rather than treating None as "no source exists".
    """
    host = (urlparse(url).hostname or "").lower()
    return _HOST_INDEX.get(host)
