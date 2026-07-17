"""Smoke test for the LLM evaluation agent.

Calls the service layer directly — no HTTP server needed. Seeds a throwaway
user with a profile, technologies, and a resume, then evaluates a stored job.

Usage (from backend/):
    python scripts/test_evaluation.py
    python scripts/test_evaluation.py <job_id>   # evaluate a specific job
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, text

from app.database import AsyncSessionLocal
from app.models.resume import Resume
from app.models.user import User
from app.services import profile_service
from app.services.evaluation_service import run_evaluation

TEST_USERNAME = "test_pipeline_user"

RESUME_SKILLS = [
    "Python", "FastAPI", "Django", "Node.js", "React.js", "Next.js",
    "TypeScript", "JavaScript", "PostgreSQL", "MongoDB", "Redis",
    "WebSockets", "REST APIs", "Machine Learning", "RAG", "Kafka", "SQL",
    "Git", "Linux",
]

RESUME_RAW = (
    "Python FastAPI Django Node.js React.js Next.js TypeScript JavaScript "
    "PostgreSQL MongoDB Redis WebSockets REST APIs Machine Learning RAG LangChain "
    "LangGraph Kafka Full Stack Backend Software Engineer. "
    "Built production RAG pipelines and AI agent workflows. "
    "2 years experience with FastAPI microservices and async Python. "
    "Contributed to open source LangChain integrations."
)


async def seed_test_data(db) -> int:
    """Create (or reuse) the test user with a profile, skills, and one resume."""
    user = (
        await db.execute(select(User).where(User.username == TEST_USERNAME))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            username=TEST_USERNAME,
            email="test@pipeline.local",
            password_hash="not-a-real-hash",
        )
        db.add(user)
        await db.flush()

    resume = (
        await db.execute(select(Resume).where(Resume.user_id == user.id))
    ).scalar_one_or_none()
    if resume is None:
        db.add(
            Resume(
                user_id=user.id,
                file_name="aneeb_resume.pdf",
                parsed_content={"skills": RESUME_SKILLS, "experience": [], "education": []},
                raw_content=RESUME_RAW,
            )
        )
    await db.commit()

    await profile_service.update_profile(db, user.id, {"technologies": RESUME_SKILLS})
    return user.id


async def pick_job(db, job_id_arg: str | None) -> tuple[int, str, str]:
    if job_id_arg:
        row = (
            await db.execute(
                text(
                    "SELECT j.id, j.title, c.name AS company FROM jobs j "
                    "JOIN companies c ON c.id = j.company_id WHERE j.id = :id"
                ),
                {"id": int(job_id_arg)},
            )
        ).one()
        return row.id, row.title, row.company

    # Default: pick a job that has a description so the eval is meaningful
    row = (
        await db.execute(
            text(
                """
                SELECT j.id, j.title, c.name AS company
                FROM jobs j
                JOIN companies c ON c.id = j.company_id
                WHERE j.description IS NOT NULL
                ORDER BY random()
                LIMIT 1
                """
            )
        )
    ).one()
    return row.id, row.title, row.company


async def main() -> None:
    job_id_arg = sys.argv[1] if len(sys.argv) > 1 else None

    async with AsyncSessionLocal() as db:
        print("Seeding test user + profile + resume...")
        user_id = await seed_test_data(db)

        job_id, title, company = await pick_job(db, job_id_arg)
        print(f"\nEvaluating: {title} @ {company}")
        print(f"Job ID    : {job_id}")
        print("\nRunning LLM evaluation (Groq -> Gemini -> OpenAI, 10-30 seconds)...\n")

        evaluation = await run_evaluation(db=db, user_id=user_id, job_id=job_id)

    print("=" * 60)
    print(f"MATCH SCORE: {evaluation.match_score}/100")
    print("=" * 60)

    print("\nSTRENGTHS")
    for i, s in enumerate(evaluation.strengths, 1):
        print(f"  {i}. {s}")

    print("\nWEAKNESSES")
    for i, w in enumerate(evaluation.weaknesses, 1):
        print(f"  {i}. {w}")

    print("\nRECOMMENDATIONS")
    for i, r in enumerate(evaluation.recommendations, 1):
        print(f"  {i}. {r}")

    print(f"\nEvaluation ID: {evaluation.id}")
    print("Stored in DB  : evaluations table")


if __name__ == "__main__":
    asyncio.run(main())
