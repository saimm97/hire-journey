from app.sources.base import BaseATSSource, RawJob, parse_datetime

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"


def _locations(job: dict) -> str:
    """Join primary + secondary locations. A single Ashby posting can span cities,
    so taking only `location` silently drops the rest."""
    names = [job.get("location") or ""]
    names += [(sec or {}).get("location", "") for sec in job.get("secondaryLocations") or []]
    return "; ".join(dict.fromkeys(n for n in names if n))


class AshbySource(BaseATSSource):
    name = "ashby"
    hosts = ("jobs.ashbyhq.com",)

    def _list_url(self, company_slug: str) -> str:
        return ASHBY_API.format(slug=company_slug)

    def _parse(self, raw: dict, company_name: str) -> RawJob | None:
        url = raw.get("jobUrl", "")
        # isListed=False means the company pulled it from their public board.
        if not url or raw.get("isListed") is False:
            return None
        return RawJob(
            title=raw.get("title", ""),
            url=url,
            company=company_name,
            location=_locations(raw),
            description=raw.get("descriptionPlain", "") or "",
            source_name=self.name,
            posted_at=parse_datetime(raw.get("publishedAt")),
        )
