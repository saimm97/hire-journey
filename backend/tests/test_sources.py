"""Contract tests for the ATS adapter registry.

These guard the invariants a new adapter must satisfy, so that registering one
in SOURCES is genuinely the only wiring step required.
"""

from datetime import datetime

import pytest

from app.sources import SOURCES, source_for_url
from app.sources.base import JobSource, parse_datetime, strip_html
from app.sources.lever import _from_epoch_millis


@pytest.mark.parametrize("name,source", SOURCES.items())
def test_adapter_satisfies_contract(name: str, source: JobSource):
    """Every registered adapter exposes the full JobSource surface."""
    assert source.name == name, "registry key must match the adapter's own name"
    assert source.hosts, "adapter must declare at least one posting host"
    assert callable(source.fetch)
    assert callable(source.fetch_description)


def test_hosts_are_unique_across_adapters():
    """Two adapters claiming one host would make URL routing ambiguous."""
    seen: dict[str, str] = {}
    for name, source in SOURCES.items():
        for host in source.hosts:
            assert host not in seen, f"{host} claimed by both {seen.get(host)} and {name}"
            seen[host] = name


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://boards.greenhouse.io/acme/jobs/123", "greenhouse"),
        ("https://job-boards.greenhouse.io/acme/jobs/123", "greenhouse"),
        ("https://jobs.lever.co/acme/2b1c-uuid", "lever"),
        ("https://jobs.ashbyhq.com/acme/2b1c-uuid", "ashby"),
        ("https://BOARDS.GREENHOUSE.IO/acme/jobs/123", "greenhouse"),  # host is case-insensitive
    ],
)
def test_source_for_url_routes_known_hosts(url: str, expected: str):
    resolved = source_for_url(url)
    assert resolved is not None
    assert resolved.name == expected


@pytest.mark.parametrize("url", ["https://careers.acme.com/jobs/9", "not-a-url", ""])
def test_source_for_url_returns_none_for_unknown(url: str):
    """Unknown hosts resolve to None so callers can fall back to trying all."""
    assert source_for_url(url) is None


async def test_description_capable_adapters_answer_none_when_list_api_suffices():
    """Ashby and Lever include descriptions in fetch(), so there is nothing to back-fill."""
    for name in ("ashby", "lever"):
        assert await SOURCES[name].fetch_description("acme", "https://example.com/x") is None


def test_greenhouse_requests_descriptions_in_the_list_call():
    """Without content=true the list API omits descriptions and each one costs a request."""
    from app.sources.greenhouse import GREENHOUSE_LIST_API

    assert "content=true" in GREENHOUSE_LIST_API


def test_strip_html_handles_entity_encoded_markup():
    """Greenhouse double-encodes: entities wrap the tags, so unescape must precede stripping."""
    assert strip_html("&lt;p&gt;Hello&lt;/p&gt;  &lt;b&gt;world&lt;/b&gt;") == "Hello world"
    assert strip_html("<p>Plain   HTML</p>") == "Plain HTML"
    assert strip_html(None) == ""
    assert strip_html("") == ""


@pytest.mark.parametrize(
    "value,expected_year",
    [("2026-06-22T10:35:43-04:00", 2026), ("2026-04-07T16:10:24+00:00", 2026)],
)
def test_parse_datetime_accepts_offset_aware_iso(value: str, expected_year: int):
    parsed = parse_datetime(value)
    assert isinstance(parsed, datetime)
    assert parsed.year == expected_year


@pytest.mark.parametrize("value", [None, "", "not-a-date", 12345, {"a": 1}])
def test_parse_datetime_never_raises_on_bad_input(value):
    """A malformed date from one board must not abort an entire scan."""
    assert parse_datetime(value) is None


def test_lever_epoch_millis_parsed_as_millis_not_seconds():
    """1711403416463 is March 2024 in millis; treating it as seconds gives year 56209."""
    parsed = _from_epoch_millis(1711403416463)
    assert parsed is not None
    assert parsed.year == 2024
    assert _from_epoch_millis("2024-03-25") is None
    assert _from_epoch_millis(None) is None
