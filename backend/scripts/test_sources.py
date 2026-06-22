"""
Quick smoke test for ATS source adapters.
Run from backend/: python scripts/test_sources.py
"""
import asyncio
import sys

sys.path.append(".")

from app.sources.greenhouse import GreenhouseSource
from app.sources.ashby import AshbySource
from app.sources.lever import LeverSource


async def test_source(name, source, slug, company):
    print(f"\n{'='*50}")
    print(f"Testing {name} — {company} (slug: {slug})")
    print("="*50)
    try:
        jobs = await source.fetch(slug, company)
        if not jobs:
            print("⚠ No jobs returned — company may have no open roles right now")
            return

        print(f"✓ {len(jobs)} jobs returned\n")
        for job in jobs[:3]:  # show first 3 only
            print(f"  Title    : {job.title}")
            print(f"  Company  : {job.company}")
            print(f"  Location : {job.location or 'Not specified'}")
            print(f"  URL      : {job.url}")
            print()

        if len(jobs) > 3:
            print(f"  ... and {len(jobs) - 3} more")

    except Exception as e:
        print(f"✗ Failed: {e}")


async def main():
    greenhouse = GreenhouseSource()
    ashby = AshbySource()
    lever = LeverSource()

    await test_source("Greenhouse", greenhouse, "anthropic", "Anthropic")
    await test_source("Greenhouse", greenhouse, "vercel", "Vercel")
    await test_source("Greenhouse", greenhouse, "runwayml", "Runway")
    await test_source("Ashby", ashby, "cohere", "Cohere")
    await test_source("Ashby", ashby, "elevenlabs", "ElevenLabs")
    await test_source("Ashby", ashby, "langchain", "LangChain")
    await test_source("Lever", lever, "mistral", "Mistral AI")
    await test_source("Lever", lever, "wandb", "Weights & Biases")


if __name__ == "__main__":
    asyncio.run(main())
