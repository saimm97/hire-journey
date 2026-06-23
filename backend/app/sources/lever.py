import httpx

from app.sources.base import RawJob, TIMEOUT, _HTML_TAG

LEVER_API = "https://api.lever.co/v0/postings/{slug}"


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
            desc_parts = [j.get("descriptionPlain", "") or ""]
            for section in j.get("lists", []):
                label = section.get("text", "")
                content = _HTML_TAG.sub(" ", section.get("content", "") or "").strip()
                if label and content:
                    desc_parts.append(f"{label}: {content}")
            jobs.append(RawJob(
                title=j.get("text", ""),
                url=j.get("hostedUrl", ""),
                company=company_name,
                location=j.get("categories", {}).get("location", ""),
                description=" ".join(filter(None, desc_parts)),
                source_name=self.name,
            ))
        return jobs
