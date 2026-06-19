import httpx

from app.sources.base import RawJob

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
TIMEOUT = 10.0


class AshbySource:
    name = "ashby"

    async def fetch(self, company_slug: str, company_name: str) -> list[RawJob]:
        url = ASHBY_API.format(slug=company_slug)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        jobs = []
        for j in data.get("jobs", []):
            compensation = j.get("compensation", {}) or {}
            jobs.append(RawJob(
                title=j.get("title", ""),
                url=j.get("jobUrl", ""),
                company=company_name,
                location=j.get("location", ""),
                source_name=self.name,
            ))
        return jobs
