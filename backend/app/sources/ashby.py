from app.sources.base import (
    BaseATSSource,
    RawJob,
    parse_datetime,
)
from app.sources.salary_parser import extract_salary_range, parse_salary_amount

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"


def _locations(job: dict) -> str:
    """Join primary + secondary locations. A single Ashby posting can span cities,
    so taking only `location` silently drops the rest."""
    names = [job.get("location") or ""]
    names += [(sec or {}).get("location", "") for sec in job.get("secondaryLocations") or []]
    return "; ".join(dict.fromkeys(n for n in names if n))


def _salary_range(job: dict) -> tuple[int | None, int | None]:
    compensation = job.get("compensation") or {}
    components = compensation.get("summaryComponents") or []
    salary_components = [
        component
        for component in components
        if isinstance(component, dict)
        and component.get("compensationType") == "Salary"
        and (not component.get("interval") or "YEAR" in str(component.get("interval")).upper())
    ]
    minimums = [
        value
        for component in salary_components
        if (value := parse_salary_amount(component.get("minValue"))) is not None
    ]
    maximums = [
        value
        for component in salary_components
        if (value := parse_salary_amount(component.get("maxValue"))) is not None
    ]
    if minimums or maximums:
        return min(minimums) if minimums else None, max(maximums) if maximums else None

    # Some Ashby boards publish only the display summary, while others type
    # compensation directly into the job description instead of configuring
    # Ashby's structured compensation fields.
    summary = compensation.get("scrapeableCompensationSalarySummary")
    from_summary = extract_salary_range(summary, require_salary_context=False)
    if from_summary != (None, None):
        return from_summary
    return extract_salary_range(job.get("descriptionPlain"))


class AshbySource(BaseATSSource):
    name = "ashby"
    hosts = ("jobs.ashbyhq.com",)
    feed_hosts = ("api.ashbyhq.com",)

    def _list_url(self, company_slug: str) -> str:
        return ASHBY_API.format(slug=company_slug)

    def _parse(self, raw: dict, company_name: str) -> RawJob | None:
        url = raw.get("jobUrl", "")
        # isListed=False means the company pulled it from their public board.
        if not url or raw.get("isListed") is False:
            return None
        salary_min, salary_max = _salary_range(raw)
        return RawJob(
            title=raw.get("title", ""),
            url=url,
            company=company_name,
            location=_locations(raw),
            description=raw.get("descriptionPlain", "") or "",
            source_name=self.name,
            posted_at=parse_datetime(raw.get("publishedAt")),
            salary_min=salary_min,
            salary_max=salary_max,
        )
