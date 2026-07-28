"""Shared contract and HTTP plumbing for ATS adapters.

Adding a new ATS is: implement JobSource in a new module, register it in
SOURCES (sources/__init__.py). Nothing outside app/sources/ needs to change —
callers dispatch through the registry, never by importing a vendor directly.
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

TIMEOUT = 10.0
MAX_RESPONSE_BYTES = 50 * 1024 * 1024
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

# Transient failures worth retrying. 4xx other than 429 mean "this slug isn't on
# this board" — a normal, expected outcome we must not retry or the scan crawls.
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_MAX_REDIRECTS = 3

# Keep-alive pool shared by every adapter. A scan issues one request per
# (company, adapter) pair against a handful of ATS hosts, so reusing
# connections avoids paying a TCP+TLS handshake on nearly every request.
_MAX_CONNECTIONS = 20
_MAX_KEEPALIVE = 10

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return the shared HTTP client, creating it on first use.

    Created lazily rather than at import time: an AsyncClient binds to the
    event loop that is running when it is constructed, and at import time
    there is none.
    """
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=TIMEOUT,
            # Redirect targets are followed manually only after their hostname
            # passes the same allowlist as the original feed.
            follow_redirects=False,
            limits=httpx.Limits(
                max_connections=_MAX_CONNECTIONS,
                max_keepalive_connections=_MAX_KEEPALIVE,
            ),
        )
    return _client


async def close_client() -> None:
    """Close the shared client. Called from the FastAPI lifespan on shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    """Seconds to wait before the next attempt: Retry-After if the board sent one,
    otherwise exponential backoff (1s, 2s, 4s...)."""
    header = response.headers.get("Retry-After")
    if header:
        try:
            return min(float(header), 30.0)
        except ValueError:
            pass
    return float(2**attempt)


def _validate_fetch_url(url: str, allowed_hosts: tuple[str, ...]) -> None:
    """Reject non-HTTPS, credentialed, or off-provider feed URLs."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() != "https"
        or host not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Unsupported or unsafe ATS feed URL")


async def _get_with_safe_redirects(
    client: httpx.AsyncClient,
    url: str,
    allowed_hosts: tuple[str, ...],
) -> httpx.Response:
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        response = await client.get(current_url)
        if not response.is_redirect:
            return response
        location = response.headers.get("Location")
        if not location:
            raise ValueError("ATS redirect is missing a target")
        current_url = urljoin(str(response.url), location)
        _validate_fetch_url(current_url, allowed_hosts)
    raise ValueError("ATS response exceeded the redirect limit")


async def fetch_json(url: str, *, allowed_hosts: tuple[str, ...] | None = None) -> Any:
    """GET a board endpoint and return parsed JSON, retrying transient failures.

    Shared by every adapter so retry/backoff is written once. Raises on a
    non-retryable error status — callers (fetch_service) treat that as
    "this company isn't on this board" and move on.
    """
    if allowed_hosts is None:
        original_host = (urlparse(url).hostname or "").lower()
        allowed_hosts = (original_host,)
    _validate_fetch_url(url, allowed_hosts)

    client = get_client()
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = await _get_with_safe_redirects(client, url, allowed_hosts)
        except httpx.TransportError:
            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(float(2**attempt))
                continue
            raise
        _validate_fetch_url(str(response.url), allowed_hosts)
        if response.status_code in _RETRY_STATUSES and attempt < _MAX_ATTEMPTS - 1:
            delay = _retry_delay(response, attempt)
            logger.debug("%s → %s, retrying in %.1fs", url, response.status_code, delay)
            await asyncio.sleep(delay)
            continue
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit():
            if int(content_length) > MAX_RESPONSE_BYTES:
                raise ValueError("ATS response exceeds the configured size limit")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ValueError("ATS response exceeds the configured size limit")
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError("ATS response is not valid JSON") from exc


def strip_html(raw: str | None) -> str:
    """Turn a board's HTML description into flat text.

    Some boards (Greenhouse) return HTML that is itself entity-encoded, so
    unescape first, then drop tags, then collapse the whitespace the tags left.
    """
    if not raw:
        return ""
    # Several Greenhouse boards double-encode both tags and spaces
    # ("&amp;nbsp;"). Decode twice before removing markup so descriptions and
    # compensation ranges become ordinary searchable text.
    decoded = unescape(unescape(raw))
    return _WHITESPACE.sub(" ", _HTML_TAG.sub(" ", decoded)).strip()


def parse_datetime(value: Any) -> datetime | None:
    """Best-effort ISO-8601 → datetime. Returns None for missing or malformed input.

    Boards disagree on date formats and some send null for fields they don't use,
    so a bad value must never abort a scan.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        logger.debug("unparseable datetime: %r", value)
        return None


@dataclass
class RawJob:
    title: str
    url: str
    company: str
    location: str
    description: str = ""
    source_name: str = ""
    posted_at: datetime | None = None
    deadline: datetime | None = None
    salary_min: int | None = None
    salary_max: int | None = None


class JobSource(Protocol):
    name: str
    # Hostnames this board serves its postings from. Used to route a stored job
    # back to the adapter that produced it — the posting URL is the only origin
    # marker we persist, so adapters must declare their hosts.
    hosts: tuple[str, ...]
    # Public API hosts accepted for company.careers_url. These are intentionally
    # separate from the human-facing posting hosts above.
    feed_hosts: tuple[str, ...]

    def build_list_url(self, company_slug: str) -> str:
        """Return the public job-feed URL for a company board slug."""
        ...

    async def fetch(self, company_slug: str, company_name: str) -> list[RawJob]:
        """Return every posting on this board for the given company slug."""
        ...

    async def fetch_url(self, feed_url: str, company_name: str) -> list[RawJob]:
        """Fetch the exact allowlisted feed URL stored for a company."""
        ...

    async def fetch_description(self, company_slug: str, job_url: str) -> str | None:
        """Fetch one posting's description, for boards whose list API omits it.

        Return None when this board already supplies descriptions in fetch()
        (so there is nothing to back-fill) or when the lookup fails — callers
        treat None as "no description available", never as an error.
        """
        ...


class BaseATSSource(ABC):
    """Template-method base for ATS adapters.

    fetch() is fixed here — hit the board's list endpoint, walk the postings,
    map each one, drop the skips. Subclasses supply only the two things that
    genuinely differ per provider: the list URL and how to turn one raw posting
    into a RawJob. Boards that wrap postings under a different key (or return a
    bare array, like Lever) override _iter_raw.

    Structurally satisfies the JobSource Protocol, so instances slot straight
    into the SOURCES registry. Subclasses must set `name` and `hosts`.
    """

    name: str
    hosts: tuple[str, ...]
    feed_hosts: tuple[str, ...]

    @abstractmethod
    def _list_url(self, company_slug: str) -> str:
        """The board's list endpoint for this company slug."""

    @abstractmethod
    def _parse(self, raw: dict, company_name: str) -> RawJob | None:
        """Map one raw posting to a RawJob, or None to skip it (junk/unlisted)."""

    def _iter_raw(self, data: Any) -> Iterable[dict]:
        """Extract the postings list from the raw response. Default assumes a
        ``{"jobs": [...]}`` envelope; override for other shapes."""
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise TypeError("expected a jobs list")
        return data["jobs"]

    def build_list_url(self, company_slug: str) -> str:
        """Return the provider URL used to list this company's public jobs."""
        return self._list_url(company_slug)

    async def fetch(self, company_slug: str, company_name: str) -> list[RawJob]:
        return await self.fetch_url(self.build_list_url(company_slug), company_name)

    async def fetch_url(self, feed_url: str, company_name: str) -> list[RawJob]:
        """Fetch and parse one exact provider feed URL.

        Invalid records are skipped individually so one malformed posting does
        not discard an otherwise valid board snapshot. A malformed response
        envelope still raises because it cannot be treated as a complete board.
        """
        data = await fetch_json(feed_url, allowed_hosts=self.feed_hosts)
        try:
            raw_items = self._iter_raw(data)
        except (AttributeError, TypeError) as exc:
            raise ValueError(f"Invalid {self.name} job-feed response") from exc

        jobs = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                logger.warning("%s returned a non-object job record", self.name)
                continue
            try:
                job = self._parse(raw, company_name)
            except (AttributeError, TypeError, ValueError):
                logger.warning("%s returned a malformed job record", self.name)
                continue
            if job is not None:
                jobs.append(job)
        return jobs

    async def fetch_description(self, company_slug: str, job_url: str) -> str | None:
        """Default: the list API already carries descriptions, nothing to fetch.
        Boards whose list endpoint omits them (Greenhouse) override this."""
        return None
