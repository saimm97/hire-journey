"""Contract tests for the ATS adapter registry.

These guard the invariants a new adapter must satisfy, so that registering one
in SOURCES is genuinely the only wiring step required.
"""

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from app.sources import (
    SOURCES,
    build_job_feed_url,
    normalize_board_slug,
    source_for_feed_url,
    source_for_url,
    supports_provider,
)
from app.sources.ashby import AshbySource
from app.sources.base import (
    JobSource,
    parse_datetime,
    strip_html,
)
from app.sources.greenhouse import GreenhouseSource
from app.sources.lever import LeverSource, _from_epoch_millis
from app.sources.salary_parser import extract_salary_range, parse_salary_amount


@pytest.mark.parametrize("name,source", SOURCES.items())
def test_adapter_satisfies_contract(name: str, source: JobSource):
    """Every registered adapter exposes the full JobSource surface."""
    assert source.name == name, "registry key must match the adapter's own name"
    assert source.hosts, "adapter must declare at least one posting host"
    assert source.feed_hosts, "adapter must declare at least one API feed host"
    assert callable(source.build_list_url)
    assert callable(source.fetch)
    assert callable(source.fetch_url)
    assert callable(source.fetch_description)


def test_hosts_are_unique_across_adapters():
    """Two adapters claiming one host would make URL routing ambiguous."""
    seen: dict[str, str] = {}
    for name, source in SOURCES.items():
        for host in source.hosts:
            assert host not in seen, f"{host} claimed by both {seen.get(host)} and {name}"
            seen[host] = name


def test_feed_hosts_are_unique_across_adapters():
    seen: dict[str, str] = {}
    for name, source in SOURCES.items():
        for host in source.feed_hosts:
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


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true",
            "greenhouse",
        ),
        ("https://api.lever.co/v0/postings/acme", "lever"),
        ("https://api.eu.lever.co/v0/postings/acme", "lever"),
        ("https://api.ashbyhq.com/posting-api/job-board/acme", "ashby"),
    ],
)
def test_source_for_feed_url_routes_to_one_adapter(url: str, expected: str):
    source = source_for_feed_url(url)
    assert source is not None
    assert source.name == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://boards-api.greenhouse.io/v1/boards/acme/jobs",
        "https://user:password@api.lever.co/v0/postings/acme",
        "https://api.lever.co:444/v0/postings/acme",
        "https://careers.example.com/jobs.json",
        "not-a-url",
    ],
)
def test_source_for_feed_url_rejects_unsafe_or_unknown_urls(url: str):
    assert source_for_feed_url(url) is None


async def test_description_capable_adapters_answer_none_when_list_api_suffices():
    """Ashby and Lever include descriptions in fetch(), so there is nothing to back-fill."""
    for name in ("ashby", "lever"):
        assert await SOURCES[name].fetch_description("acme", "https://example.com/x") is None


def test_greenhouse_requests_descriptions_in_the_list_call():
    """Without content=true the list API omits descriptions and each one costs a request."""
    from app.sources.greenhouse import GREENHOUSE_LIST_API

    assert "content=true" in GREENHOUSE_LIST_API


@pytest.mark.parametrize(
    "provider,slug,expected",
    [
        (
            "greenhouse",
            "blackforestlabs",
            "https://boards-api.greenhouse.io/v1/boards/blackforestlabs/jobs?content=true",
        ),
        ("lever", "netflix", "https://api.lever.co/v0/postings/netflix"),
        (
            "ashby",
            "linear",
            "https://api.ashbyhq.com/posting-api/job-board/linear?includeCompensation=true",
        ),
    ],
)
def test_build_job_feed_url(provider: str, slug: str, expected: str):
    assert build_job_feed_url(provider, slug) == expected


@pytest.mark.parametrize(
    "provider,slug",
    [
        ("workday", "acme"),
        ("greenhouse", ""),
        ("lever", "../admin"),
        ("ashby", "acme?includeHidden=true"),
    ],
)
def test_build_job_feed_url_rejects_unsupported_or_unsafe_values(provider: str, slug: str):
    with pytest.raises(ValueError):
        build_job_feed_url(provider, slug)


def test_every_configured_company_has_a_valid_slug_and_supported_sources_build_urls():
    config_path = Path(__file__).parent.parent / "config" / "companies.yaml"
    with config_path.open() as config_file:
        companies = yaml.safe_load(config_file).get("companies", [])

    assert companies
    for company in companies:
        slug = normalize_board_slug(company["slug"])
        if supports_provider(company["source"]):
            feed_url = build_job_feed_url(company["source"], slug)
            assert feed_url.startswith("https://")


def test_strip_html_handles_entity_encoded_markup():
    """Greenhouse double-encodes: entities wrap the tags, so unescape must precede stripping."""
    assert strip_html("&lt;p&gt;Hello&lt;/p&gt;  &lt;b&gt;world&lt;/b&gt;") == "Hello world"
    assert strip_html("<p>Plain   HTML</p>") == "Plain HTML"
    assert strip_html("Pay:&amp;nbsp;$100K") == "Pay: $100K"
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


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "The base salary range for this role is $166,000–$244,000 USD annually.",
            (166_000, 244_000),
        ),
        ("Compensation range: £81K to £87K.", (81_000, 87_000)),
        ("ESP base pay range per year: €86 000 - €122 000.", (86_000, 122_000)),
        ("CAN base pay range per year: $133 ,000 - $183,000.", (133_000, 183_000)),
        ("Salary range 120000-150000 based on experience.", (120_000, 150_000)),
    ],
)
def test_extract_salary_range_from_explicit_salary_text(text: str, expected: tuple[int, int]):
    assert extract_salary_range(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Candidates need 5-10 years of experience. We offer a competitive salary.",
        "Employees receive a $10-$20 monthly phone discount.",
        "Pay range: $15-$16 hourly.",
        "Annual salary range: ₹3-₹6 LPA.",
        "The annual base salary range is $300,00 - $367,000.",
        "The role was planned between 2024-2026.",
        "Compensation range unavailable. Reference JR: 2026-7464.",
    ],
)
def test_extract_salary_range_rejects_unrelated_numeric_ranges(text: str):
    assert extract_salary_range(text) == (None, None)


def test_extract_salary_range_handles_double_encoded_ats_spacing_before_job_id():
    description = strip_html(
        "Compensation Range:&amp;nbsp; $192,800.00 -&amp;nbsp; $241,000.00 "
        "*Remote role JR: 2026-7464"
    )
    assert extract_salary_range(description) == (192_800, 241_000)


@pytest.mark.parametrize("value", [None, True, -1, 0, 999, float("inf"), "120000"])
def test_parse_salary_amount_rejects_invalid_structured_values(value):
    assert parse_salary_amount(value) is None


def test_ashby_extracts_structured_salary_component():
    parsed = AshbySource()._parse(
        {
            "title": "Product Engineer",
            "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
            "location": "Remote",
            "descriptionPlain": "Build the product.",
            "compensation": {
                "summaryComponents": [
                    {
                        "compensationType": "Salary",
                        "minValue": 150000,
                        "maxValue": 189000,
                        "currencyCode": "USD",
                        "interval": "1 YEAR",
                    }
                ]
            },
        },
        "Acme",
    )

    assert parsed is not None
    assert (parsed.salary_min, parsed.salary_max) == (150_000, 189_000)


def test_ashby_extracts_salary_typed_only_in_description():
    parsed = AshbySource()._parse(
        {
            "title": "Product Engineer",
            "jobUrl": "https://jobs.ashbyhq.com/acme/job-2",
            "location": "Remote",
            "descriptionPlain": "The base salary range is $130K - $175K per year.",
            "compensation": {},
        },
        "Acme",
    )

    assert parsed is not None
    assert (parsed.salary_min, parsed.salary_max) == (130_000, 175_000)


def test_lever_extracts_structured_salary_range():
    parsed = LeverSource()._parse(
        {
            "text": "Backend Engineer",
            "hostedUrl": "https://jobs.lever.co/acme/job-1",
            "descriptionPlain": "Build services.",
            "salaryRange": {
                "min": 105000,
                "max": 145000,
                "currency": "USD",
                "interval": "per-year-salary",
            },
        },
        "Acme",
    )

    assert parsed is not None
    assert (parsed.salary_min, parsed.salary_max) == (105_000, 145_000)


def test_lever_rejects_explicit_hourly_salary_range():
    parsed = LeverSource()._parse(
        {
            "text": "Store Manager",
            "hostedUrl": "https://jobs.lever.co/acme/job-2",
            "descriptionPlain": "Pay range: $25-$30 hourly.",
            "salaryRange": {
                "min": 25,
                "max": 30,
                "currency": "USD",
                "interval": "per-hour-wage",
            },
        },
        "Acme",
    )

    assert parsed is not None
    assert (parsed.salary_min, parsed.salary_max) == (None, None)


def test_greenhouse_converts_pay_transparency_cents_to_salary_units():
    parsed = GreenhouseSource()._parse(
        {
            "title": "Platform Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
            "location": {"name": "Remote"},
            "content": "Build the platform.",
            "pay_input_ranges": [
                {"min_cents": 12_500_000, "max_cents": 18_000_000, "currency_type": "USD"}
            ],
        },
        "Acme",
    )

    assert parsed is not None
    assert (parsed.salary_min, parsed.salary_max) == (125_000, 180_000)
