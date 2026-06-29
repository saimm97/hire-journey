import httpx

from app.sources.base import RawJob, TIMEOUT

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"


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
            jobs.append(RawJob(
                title=j.get("title", ""),
                url=j.get("jobUrl", ""),
                company=company_name,
                location=j.get("location", ""),
                description=j.get("descriptionPlain", "") or "",
                source_name=self.name,
            ))
        return jobs
