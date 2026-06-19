import httpx

from app.sources.base import RawJob

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
TIMEOUT = 10.0


class GreenhouseSource:
    name = "greenhouse"

    async def fetch(self, company_slug: str, company_name: str) -> list[RawJob]:
        url = GREENHOUSE_API.format(slug=company_slug)
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
