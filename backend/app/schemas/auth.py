"""Pydantic schemas for the authentication API.

These define the *shape* of data crossing the HTTP boundary — what a client may
send and what it receives back. They are deliberately separate from the ORM
``User`` model so the password hash is never serialized to a response.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Request body for ``POST /auth/register``.

    Field constraints mirror the database columns (username/email lengths) and
    enforce a minimum password strength before anything is hashed or stored.
    """

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    """Public representation of a user — every field here is safe to expose.

    ``from_attributes`` lets FastAPI build this directly from a SQLAlchemy
    ``User`` instance. The ``password_hash`` column is intentionally absent.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    """Response body for a successful login: a bearer token for the client to store."""

    access_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    """Request body for ``POST /auth/google``.

    ``credential`` is the ID token (a signed JWT) returned by Google Identity
    Services in the browser — not our own access token.
    """

    credential: str


class AuthConfig(BaseModel):
    """Non-secret auth settings the frontend needs at load time.

    The Google client id is public by design (it ships in the browser), so
    serving it here keeps a single source of truth in the backend ``.env``
    instead of duplicating it in frontend code.
    """

    google_enabled: bool
    google_client_id: str
