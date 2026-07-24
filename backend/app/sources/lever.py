from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from app.sources.base import BaseATSSource, RawJob, strip_html

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


class LeverSource(BaseATSSource):
    name = "lever"
    hosts = ("jobs.lever.co",)

    def _list_url(self, company_slug: str) -> str:
        return LEVER_API.format(slug=company_slug)

    def _iter_raw(self, data: Any) -> Iterable[dict]:
        return data  # Lever returns a root array, no {"jobs": ...} wrapper

    def _parse(self, raw: dict, company_name: str) -> RawJob | None:
        url = raw.get("hostedUrl", "")
        if not url:
            return None
        return RawJob(
            title=raw.get("text", ""),
            url=url,
            company=company_name,
            location=_locations(raw),
            description=_description(raw),
            source_name=self.name,
            posted_at=_from_epoch_millis(raw.get("createdAt")),
        )
