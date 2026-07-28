"""Shared contract and HTTP plumbing for ATS adapters.

Adding a new ATS is: implement JobSource in a new module, then add one provider
registration in sources/__init__.py. Nothing outside app/sources/ needs to
change — callers dispatch through the registry, never by importing a vendor
directly.
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from contextlib import aclosing
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx

from app.config import settings
from app.sources.url_policy import validate_ats_url

logger = logging.getLogger(__name__)

_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

# Transient failures worth retrying. 4xx other than 429 mean "this slug isn't on
# this board" — a normal, expected outcome we must not retry or the scan crawls.
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_REDIRECTS = 3
_READ_CHUNK_BYTES = 64 * 1024

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
            timeout=settings.ats_http_timeout_seconds,
            # Redirect targets are followed manually only after their hostname
            # passes the same allowlist as the original feed.
            follow_redirects=False,
            limits=httpx.Limits(
                max_connections=settings.ats_http_max_connections,
                max_keepalive_connections=settings.ats_http_max_keepalive_connections,
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


async def _send_with_safe_redirects(
    client: httpx.AsyncClient,
    url: str,
    allowed_hosts: tuple[str, ...],
) -> httpx.Response:
    """Return one open streamed response after validating every redirect hop.

    The caller owns the returned response. Redirect responses are closed here
    before another connection is opened.
    """
    current_url = url
    for _ in range(_MAX_REDIRECTS + 1):
        request = client.build_request("GET", current_url)
        response = await client.send(request, stream=True)
        if not response.is_redirect:
            return response
        try:
            location = response.headers.get("Location")
            if not location:
                raise ValueError("ATS redirect is missing a target")
            current_url = urljoin(str(response.url), location)
            validate_ats_url(current_url, allowed_hosts=allowed_hosts)
        finally:
            await response.aclose()
    raise ValueError("ATS response exceeded the redirect limit")


async def _read_limited_response(response: httpx.Response) -> bytes:
    """Read a streamed response while enforcing the decoded-body memory cap."""
    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit():
        if int(content_length) > settings.ats_max_response_bytes:
            raise ValueError("ATS response exceeds the configured size limit")

    content = bytearray()
    exceeded_limit = False
    async with aclosing(response.aiter_bytes(chunk_size=_READ_CHUNK_BYTES)) as chunks:
        async for chunk in chunks:
            if exceeded_limit:
                continue
            if len(content) + len(chunk) > settings.ats_max_response_bytes:
                # Close the network stream immediately, then let HTTPX unwind
                # its decoding iterator before raising the stable size error.
                # This avoids leaving a nested async iterator pending while
                # still preventing any additional network reads.
                exceeded_limit = True
                await response.aclose()
                continue
            content.extend(chunk)
    if exceeded_limit:
        raise ValueError("ATS response exceeds the configured size limit")
    return bytes(content)


async def fetch_json(url: str, *, allowed_hosts: tuple[str, ...] | None = None) -> Any:
    """GET a board endpoint and return parsed JSON, retrying transient failures.

    Shared by every adapter so retry/backoff is written once. Raises on a
    non-retryable error status — callers (fetch_service) treat that as
    "this company isn't on this board" and move on.
    """
    parsed = validate_ats_url(url, allowed_hosts=allowed_hosts)
    if allowed_hosts is None:
        original_host = (parsed.hostname or "").lower()
        allowed_hosts = (original_host,)

    client = get_client()
    for attempt in range(settings.ats_max_attempts):
        response: httpx.Response | None = None
        retry_delay: float | None = None
        try:
            response = await _send_with_safe_redirects(client, url, allowed_hosts)
            validate_ats_url(str(response.url), allowed_hosts=allowed_hosts)

            if response.status_code in _RETRY_STATUSES and attempt < settings.ats_max_attempts - 1:
                retry_delay = _retry_delay(response, attempt)
                logger.debug(
                    "%s → %s, retrying in %.1fs",
                    url,
                    response.status_code,
                    retry_delay,
                )
            else:
                response.raise_for_status()
                content = await _read_limited_response(response)
                try:
                    return json.loads(content)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError("ATS response is not valid JSON") from exc
        except httpx.TransportError:
            if attempt >= settings.ats_max_attempts - 1:
                raise
            retry_delay = float(2**attempt)
        finally:
            if response is not None:
                await response.aclose()

        if retry_delay is not None:
            await asyncio.sleep(retry_delay)

    raise RuntimeError("ATS retry loop exhausted unexpectedly")


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
