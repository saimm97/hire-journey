"""Shared fixtures for API integration tests against the live Postgres database."""

import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import AsyncSessionLocal, engine
from app.main import app
from app.models.user import User


@pytest_asyncio.fixture
async def db() -> AsyncIterator[AsyncSession]:
    """Yield a session for setup/teardown, then drop pooled connections tied to this loop."""
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> AsyncIterator[User]:
    """Create a throwaway user and cascade-delete it (and its candidate) after the test."""
    user = User(
        username=f"pytest-{uuid.uuid4().hex[:12]}",
        email=f"pytest-{uuid.uuid4().hex[:12]}@example.test",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    try:
        yield user
    finally:
        await db.execute(delete(User).where(User.user_id == user.user_id))
        await db.commit()


@pytest_asyncio.fixture
async def client(test_user: User) -> AsyncIterator[AsyncClient]:
    """Yield an HTTP client whose authenticated user is the throwaway test user."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
    app.dependency_overrides.pop(get_current_user, None)
