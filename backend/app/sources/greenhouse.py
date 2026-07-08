import re
from html import unescape

import httpx

from app.sources.base import RawJob, TIMEOUT, _HTML_TAG

GREENHOUSE_LIST_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
GREENHOUSE_JOB_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"

# Greenhouse job id appears in two URL shapes: the standard boards URL
# (".../jobs/12345") and custom career pages that carry it as a query param
# ("company.com/careers/?gh_jid=12345"). Match either.
_JOB_ID_RE = re.compile(r"(?:/jobs/|gh_jid=)(\d+)")


class GreenhouseSource:
    name = "greenhouse"

    async def fetch(self, company_slug: str, company_name: str) -> list[RawJob]:
        url = GREENHOUSE_LIST_API.format(slug=company_slug)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        jobs = []
        for j in data.get("jobs", []):
            jobs.append(RawJob(
                title=j.get("title", ""),
                url=j.get("absolute_url", ""),
                company=company_name,
                location=j.get("location", {}).get("name", ""),
                source_name=self.name,
            ))
        return jobs

    @staticmethod
    async def fetch_description(company_slug: str, job_url: str) -> str | None:
        """Fetch the full description for a single Greenhouse posting.

        The list API omits descriptions. This hits the individual job endpoint
        using the job_id extracted from the posting URL.
        """
        match = _JOB_ID_RE.search(job_url)
        if not match:
            return None
        job_id = match.group(1)
        url = GREENHOUSE_JOB_API.format(slug=company_slug, job_id=job_id)
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            raw = data.get("content", "") or ""
            # Greenhouse wraps HTML in HTML entities — unescape first, then strip tags
            clean = _HTML_TAG.sub(" ", unescape(raw)).strip()
            return clean or None
        except Exception:
            return None
