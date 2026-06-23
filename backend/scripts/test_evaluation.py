"""Smoke test for the LLM evaluation agent.

Calls the service layer directly — no HTTP server needed.

Usage (from backend/):
    python scripts/test_evaluation.py
    python scripts/test_evaluation.py <job_id>   # evaluate a specific job
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.resume import Resume
from app.models.user import User
from app.services.evaluation_service import run_evaluation

TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_RESUME_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

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


async def seed_test_data(db) -> None:
    await db.execute(
        pg_insert(User).values(
            user_id=TEST_USER_ID,
            username="test_pipeline_user",
            email="test@pipeline.local",
            password_hash="not-a-real-hash",
        ).on_conflict_do_nothing(index_elements=["user_id"])
    )
    await db.execute(
        pg_insert(Resume).values(
            resume_id=TEST_RESUME_ID,
            user_id=TEST_USER_ID,
            file_name="aneeb_resume.pdf",
            is_active=True,
            parsed_content={"skills": [{"name": s} for s in RESUME_SKILLS], "experience": [], "education": []},
            raw_content=RESUME_RAW,
        ).on_conflict_do_update(
            index_elements=["resume_id"],
            set_={"raw_content": RESUME_RAW},
        )
    )
    await db.commit()


async def pick_job(db, job_id_arg: str | None) -> tuple[uuid.UUID, str, str]:
    if job_id_arg:
        job_id = uuid.UUID(job_id_arg)
        row = (await db.execute(
            text("SELECT job_id, title, company_id FROM jobs WHERE job_id = :id"),
            {"id": str(job_id)},
        )).one()
        return row.job_id, row.title, str(row.company_id)

    # Default: pick a job that has a description so the eval is meaningful
    row = (await db.execute(text("""
        SELECT j.job_id, j.title, c.name as company
        FROM jobs j
        JOIN companies c ON c.company_id = j.company_id
        WHERE j.description IS NOT NULL
        ORDER BY random()
        LIMIT 1
    """))).one()
    return row.job_id, row.title, row.company


async def main() -> None:
    job_id_arg = sys.argv[1] if len(sys.argv) > 1 else None

    async with AsyncSessionLocal() as db:
        print("Seeding test user + resume...")
        await seed_test_data(db)

        job_id, title, company = await pick_job(db, job_id_arg)
        print(f"\nEvaluating: {title} @ {company}")
        print(f"Job ID    : {job_id}")
        print("\nRunning LLM evaluation (Groq → Gemini → OpenAI, 10-30 seconds)...\n")

        evaluation = await run_evaluation(
            db=db,
            user_id=TEST_USER_ID,
            job_id=job_id,
            resume_id=TEST_RESUME_ID,
        )

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
    print(f"Stored in DB  : evaluations table")


if __name__ == "__main__":
    asyncio.run(main())
