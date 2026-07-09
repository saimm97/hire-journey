"""Shared FastAPI dependencies."""

import uuid
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.config import settings
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    """Resolve a bearer token or cookie to its user, or raise 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=messages.CREDENTIALS_UNVERIFIED,
        headers=messages.AUTH_HEADER,
    )
    
    raw_token = token or access_token
    if not raw_token:
        raise unauthorized

    try:
        payload = jwt.decode(raw_token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = uuid.UUID(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise unauthorized

    user = (
        await db.execute(select(User).where(User.user_id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise unauthorized
    return user
