"""End-to-end pipeline test: seed test data → run search → print ranked results.

Calls the service layer directly (no HTTP server needed). Tests the full
fetch → filter → upsert → score → rank flow against live ATS boards.

Run from backend/:
    python scripts/test_pipeline.py
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.resume import Resume
from app.models.user import User
from app.services import search_service

# Fixed UUIDs so the script is idempotent — re-running doesn't create duplicates
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_RESUME_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

# Aneeb's actual search intent
SEARCH_TERMS = [
    "Full Stack Engineer",
    "Backend Engineer",
    "Software Engineer",
    "Python",
    "FastAPI",
    "React",
    "AI Engineer",
]

# Extracted from Aneeb's resume — what the parse agent would produce
RESUME_SKILLS = [
    {"name": "Python"},
    {"name": "FastAPI"},
    {"name": "Django"},
    {"name": "Node.js"},
    {"name": "React.js"},
    {"name": "Next.js"},
    {"name": "TypeScript"},
    {"name": "JavaScript"},
    {"name": "PostgreSQL"},
    {"name": "MongoDB"},
    {"name": "Redis"},
    {"name": "WebSockets"},
    {"name": "REST APIs"},
    {"name": "Machine Learning"},
    {"name": "RAG"},
    {"name": "Kafka"},
    {"name": "SQL"},
    {"name": "Git"},
    {"name": "Linux"},
]


async def seed_test_data(db) -> None:
    """Insert a test user and resume if they don't already exist."""
    user_stmt = (
        pg_insert(User)
        .values(
            user_id=TEST_USER_ID,
            username="test_pipeline_user",
            email="test@pipeline.local",
            password_hash="not-a-real-hash",
        )
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await db.execute(user_stmt)

    resume_stmt = (
        pg_insert(Resume)
        .values(
            resume_id=TEST_RESUME_ID,
            user_id=TEST_USER_ID,
            file_name="aneeb_resume.pdf",
            is_active=True,
            parsed_content={"skills": RESUME_SKILLS, "experience": [], "education": []},
            raw_content=(
                "Python FastAPI Django Node.js React.js Next.js TypeScript JavaScript "
                "PostgreSQL MongoDB Redis WebSockets REST APIs Machine Learning RAG LSTM Kafka "
                "Full Stack Backend Software Engineer"
            ),
        )
        .on_conflict_do_update(
            index_elements=["resume_id"],
            set_={"parsed_content": {"skills": RESUME_SKILLS, "experience": [], "education": []}},
        )
    )
    await db.execute(resume_stmt)

    await db.commit()


async def main() -> None:
    print("Career Engine — Pipeline Test")
    print("=" * 50)
    print(f"Search terms : {SEARCH_TERMS}")
    print(f"Resume skills: {[s['name'] for s in RESUME_SKILLS]}")
    print()

    async with AsyncSessionLocal() as db:
        print("Seeding test user and resume...")
        await seed_test_data(db)

        print("Running search pipeline (fetching from all 80 companies)...")
        print("This will take 10-30 seconds depending on API response times.\n")

        session, total = await search_service.run_search(
            db=db,
            user_id=TEST_USER_ID,
            resume_id=TEST_RESUME_ID,
            search_terms=SEARCH_TERMS,
        )

        print(f"Session ID   : {session.session_id}")
        print(f"Jobs scored  : {total}")
        print()

        # Top 20 results
        results = await search_service.get_results(
            db=db,
            session_id=session.session_id,
            user_id=TEST_USER_ID,
            min_score=0,
            limit=20,
            offset=0,
        )

    print(f"Top results (total matching: {results.total})")
    print("-" * 80)
    print(f"{'Score':>5}  {'Company':<20} {'Title':<40} {'Location'}")
    print("-" * 80)
    for r in results.results:
        loc = (r.location or "")[:20]
        title = r.title[:38]
        company = r.company_name[:18]
        print(f"  {r.score:>3}  {company:<20} {title:<40} {loc}")

    print()
    print(f"Full results at: GET /api/v1/search/{session.session_id}/results")


if __name__ == "__main__":
    asyncio.run(main())
