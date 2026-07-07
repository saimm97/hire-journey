"""Tests for GET /api/v1/profile — re-hydrating the onboarding snapshot."""

from httpx import AsyncClient

from app.models.user import User
from tests.helpers import seed_candidate, seed_project, seed_resume

PROFILE_URL = "/api/v1/profile"


async def test_get_returns_profile_summary_and_projects(
    client: AsyncClient, test_user: User
) -> None:
    """GET returns the candidate, the active resume's summary, and the CV projects."""
    await seed_candidate(test_user.user_id, first_name="Ada", tech_stack=["Python"])
    await seed_resume(test_user.user_id, summary="Backend engineer with 5 years.")
    await seed_project(test_user.user_id, name="Portfolio", summary="A site", tech_stack=["Next"])

    response = await client.get(PROFILE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["first_name"] == "Ada"
    assert body["profile"]["tech_stack"] == ["Python"]
    assert body["resume_summary"] == "Backend engineer with 5 years."
    assert [p["name"] for p in body["projects"]] == ["Portfolio"]


async def test_get_returns_404_when_no_candidate(client: AsyncClient, test_user: User) -> None:
    """GET 404s for a user who has not been onboarded yet."""
    response = await client.get(PROFILE_URL)

    assert response.status_code == 404
