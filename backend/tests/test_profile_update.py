"""Tests for PATCH /api/v1/profile — persisting user-edited candidate fields."""

from httpx import AsyncClient

from app.models.user import User
from tests.helpers import load_candidate, seed_candidate

PROFILE_URL = "/api/v1/profile"


async def test_patch_persists_only_provided_fields(client: AsyncClient, test_user: User) -> None:
    """A partial PATCH updates the sent fields and leaves the rest untouched."""
    await seed_candidate(
        test_user.user_id,
        first_name="Old",
        last_name="Keep",
        email="keep@example.com",
        tech_stack=["Python"],
    )

    response = await client.patch(
        PROFILE_URL, json={"first_name": "New", "tech_stack": ["Go", "Rust"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "New"
    assert body["last_name"] == "Keep"
    assert body["tech_stack"] == ["Go", "Rust"]

    stored = await load_candidate(test_user.user_id)
    assert stored.first_name == "New"
    assert stored.last_name == "Keep"
    assert stored.email == "keep@example.com"
    assert stored.tech_stack == ["Go", "Rust"]


async def test_patch_clears_fields_sent_as_null_or_empty(
    client: AsyncClient, test_user: User
) -> None:
    """An explicit null or empty value overwrites the stored field."""
    await seed_candidate(
        test_user.user_id, first_name="Ada", phone="123", tech_stack=["Python"]
    )

    response = await client.patch(PROFILE_URL, json={"phone": None, "tech_stack": []})

    assert response.status_code == 200
    stored = await load_candidate(test_user.user_id)
    assert stored.first_name == "Ada"
    assert stored.phone is None
    assert stored.tech_stack == []


async def test_patch_persists_job_preferences(client: AsyncClient, test_user: User) -> None:
    """PATCH writes the Screen 3 preference columns (desired_role, minimum_salary)."""
    await seed_candidate(test_user.user_id, first_name="Ada")

    response = await client.patch(
        PROFILE_URL,
        json={"desired_role": ["ML Engineer", "Backend Engineer"], "minimum_salary": 120000},
    )

    assert response.status_code == 200
    stored = await load_candidate(test_user.user_id)
    assert stored.desired_role == ["ML Engineer", "Backend Engineer"]
    assert stored.minimum_salary == 120000
