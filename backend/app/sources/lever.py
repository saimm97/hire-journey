from collections.abc import Iterable
from datetime import datetime, timezone
from html import escape
from typing import Any

from app.sources.base import (
    BaseATSSource,
    RawJob,
    strip_html,
)
from app.sources.html_sanitizer import sanitize_job_html
from app.sources.salary_parser import extract_salary_range, parse_salary_amount

LEVER_API = "https://api.lever.co/v0/postings/{slug}"


def _from_epoch_millis(value: object) -> datetime | None:
    """Lever sends createdAt as Unix epoch *milliseconds* (e.g. 1711403416463),
    not ISO-8601 — parsing it as a string silently yields 1970 dates."""
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _locations(job: dict) -> str:
    categories = job.get("categories") or {}
    names = [categories.get("location") or ""]
    names += categories.get("allLocations") or []  # nested under categories, not top level
    return "; ".join(dict.fromkeys(n for n in names if n))


def _description(job: dict) -> str:
    parts = [job.get("descriptionPlain", "") or ""]
    for section in job.get("lists", []):
        label = section.get("text", "")
        content = strip_html(section.get("content"))
        if label and content:
            parts.append(f"{label}: {content}")
    return " ".join(filter(None, parts))


def _description_html(job: dict) -> str:
    parts = [job.get("description", "") or ""]
    for section in job.get("lists", []):
        label = section.get("text", "")
        content = section.get("content", "")
        if label:
            parts.append(f"<h3>{escape(str(label))}</h3>")
        if content:
            parts.append(str(content))
    if additional := job.get("additional"):
        parts.append(str(additional))
    return sanitize_job_html("".join(parts))


def _salary_range(job: dict, description: str) -> tuple[int | None, int | None]:
    salary = job.get("salaryRange") or {}
    interval = str(salary.get("interval") or "").lower()
    if not interval or "year" in interval or "annual" in interval:
        minimum = parse_salary_amount(salary.get("min"))
        maximum = parse_salary_amount(salary.get("max"))
        if minimum is not None or maximum is not None:
            return minimum, maximum

    from_salary_field = extract_salary_range(
        job.get("salaryDescriptionPlain"),
        require_salary_context=False,
    )
    if from_salary_field != (None, None):
        return from_salary_field
    return extract_salary_range(description)


class LeverSource(BaseATSSource):
    name = "lever"
    hosts = ("jobs.lever.co",)
    feed_hosts = ("api.lever.co", "api.eu.lever.co")

    def _list_url(self, company_slug: str) -> str:
        return LEVER_API.format(slug=company_slug)

    def _iter_raw(self, data: Any) -> Iterable[dict]:
        if not isinstance(data, list):
            raise TypeError("expected a root job list")
        return data  # Lever returns a root array, no {"jobs": ...} wrapper

    def _parse(self, raw: dict, company_name: str) -> RawJob | None:
        url = raw.get("hostedUrl", "")
        if not url:
            return None
        plain_description = _description(raw)
        description = _description_html(raw)
        salary_min, salary_max = _salary_range(raw, plain_description)
        return RawJob(
            title=raw.get("text", ""),
            url=url,
            company=company_name,
            location=_locations(raw),
            description=description or plain_description,
            source_name=self.name,
            posted_at=_from_epoch_millis(raw.get("createdAt")),
            salary_min=salary_min,
            salary_max=salary_max,
        )
