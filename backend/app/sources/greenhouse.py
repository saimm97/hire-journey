import re

from app.sources.base import BaseATSSource, RawJob, fetch_json, parse_datetime, strip_html

# content=true returns every posting's full description in the same response.
# Without it the list API omits descriptions entirely and each one costs a
# separate request — 405 requests instead of 1 on a board the size of Anthropic's.
GREENHOUSE_LIST_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
GREENHOUSE_JOB_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"

_JOB_ID_RE = re.compile(r"/jobs/(\d+)")


class GreenhouseSource(BaseATSSource):
    name = "greenhouse"
    hosts = ("boards.greenhouse.io", "job-boards.greenhouse.io")

    def _list_url(self, company_slug: str) -> str:
        return GREENHOUSE_LIST_API.format(slug=company_slug)

    def _parse(self, raw: dict, company_name: str) -> RawJob | None:
        url = raw.get("absolute_url", "")
        if not url:
            return None
        return RawJob(
            title=raw.get("title", ""),
            url=url,
            company=company_name,
            location=(raw.get("location") or {}).get("name", ""),
            description=strip_html(raw.get("content")),
            source_name=self.name,
            # first_published is set once at posting time and never moves.
            # (updated_at also exists here — unused until we do change detection.)
            posted_at=parse_datetime(raw.get("first_published")),
            deadline=parse_datetime(raw.get("application_deadline")),
        )

    async def fetch_description(self, company_slug: str, job_url: str) -> str | None:
        """Fetch one posting's description from the per-job endpoint.

        Redundant now that fetch() requests content=true, but kept as the
        contract's fallback for jobs stored before that change, and for boards
        that return a posting without content.
        """
        match = _JOB_ID_RE.search(job_url)
        if not match:
            return None
        url = GREENHOUSE_JOB_API.format(slug=company_slug, job_id=match.group(1))
        try:
            data = await fetch_json(url)
        except Exception:
            return None
        return strip_html(data.get("content")) or None
