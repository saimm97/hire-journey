"""Tests for PUT /api/v1/profile/projects — replacing the edited CV projects."""

from httpx import AsyncClient

from app.models.user import User
from tests.helpers import load_cv_projects, seed_project

PROJECTS_URL = "/api/v1/profile/projects"


async def test_put_replaces_cv_projects(client: AsyncClient, test_user: User) -> None:
    """PUT swaps the stored CV projects for the submitted set and returns them."""
    await seed_project(test_user.user_id, name="Old Project", summary="stale")

    response = await client.put(
        PROJECTS_URL,
        json=[
            {"name": "New Project", "summary": "Does things", "tech_stack": ["Python"]},
            {"name": "Second", "tech_stack": []},
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert [p["name"] for p in body] == ["New Project", "Second"]
    assert all(p["source"] == "cv" for p in body)

    stored = await load_cv_projects(test_user.user_id)
    assert [p.name for p in stored] == ["New Project", "Second"]
    assert stored[0].tech_stack == ["Python"]
