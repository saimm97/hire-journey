"""Shared security policy for external ATS feed URLs."""

from collections.abc import Iterable
from urllib.parse import ParseResult, urlparse


def validate_ats_url(
    url: str,
    *,
    allowed_hosts: Iterable[str] | None = None,
) -> ParseResult:
    """Parse an HTTPS ATS URL or raise a safe, content-free error.

    Feed routing and redirect validation intentionally share this function so
    their SSRF protections cannot drift as new providers are registered.
    """
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        port = parsed.port
        username = parsed.username
        password = parsed.password
    except (TypeError, ValueError) as exc:
        raise ValueError("Unsupported or unsafe ATS feed URL") from exc

    normalized_hosts = (
        {allowed_host.lower() for allowed_host in allowed_hosts}
        if allowed_hosts is not None
        else None
    )
    if (
        parsed.scheme.lower() != "https"
        or not host
        or username is not None
        or password is not None
        or port not in (None, 443)
        or (normalized_hosts is not None and host not in normalized_hosts)
    ):
        raise ValueError("Unsupported or unsafe ATS feed URL")

    return parsed
