"""Registration, login, and Google sign-in logic."""

import re

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.exceptions import GoogleAuthError, InvalidCredentialsError, UserAlreadyExistsError
from app.google_oauth import verify_google_id_token
from app.models.user import User
from app.schemas.auth import UserCreate
from app.security import hash_password, verify_password


async def register_user(db: AsyncSession, payload: UserCreate) -> User:
    """Create a user, rejecting a taken username or email."""
    existing = await db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email)
        )
    )
    conflict = existing.scalars().first()
    if conflict is not None:
        raise UserAlreadyExistsError(
            "username" if conflict.username == payload.username else "email"
        )

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:  # lost a race against a concurrent signup
        await db.rollback()
        raise UserAlreadyExistsError("username or email")
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, identifier: str, password: str) -> User:
    """Return the user matching identifier (email or username) and password."""
    result = await db.execute(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError
    return user


async def _unique_username(db: AsyncSession, email: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_]", "", email.split("@")[0]) or "user"
    if len(base) < 3:
        base = f"{base}user"
    base = base[:40]
    candidate, suffix = base, 0
    while (
        await db.execute(select(User.user_id).where(User.username == candidate))
    ).first() is not None:
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


async def authenticate_google_user(db: AsyncSession, credential: str) -> User:
    """Resolve a Google ID token to a user, linking or creating as needed."""
    claims = await verify_google_id_token(credential)
    google_sub, email = claims["sub"], claims["email"]

    linked = await db.execute(select(User).where(User.google_id == google_sub))
    user = linked.scalar_one_or_none()
    if user is not None:
        return user

    existing = await db.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()
    if user is not None:
        if not claims.get("email_verified", False):  # never link an unverified email
            raise GoogleAuthError(messages.GOOGLE_EMAIL_UNVERIFIED)
        user.google_id = google_sub
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        username=await _unique_username(db, email),
        email=email,
        google_id=google_sub,
        password_hash=None,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:  # concurrent first sign-in for the same account
        await db.rollback()
        user = (
            await db.execute(select(User).where(User.google_id == google_sub))
        ).scalar_one_or_none()
        if user is None:
            raise GoogleAuthError(messages.GOOGLE_ACCOUNT_FAILED)
    else:
        await db.refresh(user)
    return user
