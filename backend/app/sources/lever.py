import httpx

from app.sources.base import RawJob

LEVER_API = "https://api.lever.co/v0/postings/{slug}"
TIMEOUT = 10.0


class LeverSource:
    name = "lever"

    async def fetch(self, company_slug: str, company_name: str) -> list[RawJob]:
        url = LEVER_API.format(slug=company_slug)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        jobs = []
        for j in data:  # Lever returns a root array, no wrapper
            jobs.append(RawJob(
                title=j.get("text", ""),
                url=j.get("hostedUrl", ""),
                company=company_name,
                location=j.get("categories", {}).get("location", ""),
                source_name=self.name,
            ))
        return jobs
