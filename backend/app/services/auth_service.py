"""Authentication business logic.

This layer owns the *rules* of registration and login — uniqueness, password
hashing, credential checks — and talks to the database through SQLAlchemy. It is
framework-agnostic: it raises plain domain exceptions instead of HTTP errors, so
it can be unit-tested without a web request and reused outside the API. The API
layer is responsible for translating these exceptions into HTTP responses.
"""

import re

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.google_oauth import GoogleAuthError, verify_google_id_token
from app.models.user import User
from app.schemas.auth import UserCreate
from app.security import hash_password, verify_password


class UserAlreadyExistsError(Exception):
    """Raised when a username or email is already taken.

    ``field`` names the conflicting column ("username" or "email") so the API
    layer can return a precise, user-friendly message.
    """

    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"{field} already registered")


class InvalidCredentialsError(Exception):
    """Raised when a login identifier and password do not match a user."""


async def register_user(db: AsyncSession, payload: UserCreate) -> User:
    """Create and persist a new user from a validated registration payload.

    Performs a friendly pre-check for an existing username/email, then relies on
    the database unique constraints as the authoritative guard against races
    between concurrent registrations. The password is hashed before storage —
    plaintext never touches the database.

    Raises:
        UserAlreadyExistsError: if the username or email is already in use.
    """
    existing = await db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email)
        )
    )
    conflict = existing.scalars().first()
    if conflict is not None:
        field = "username" if conflict.username == payload.username else "email"
        raise UserAlreadyExistsError(field)

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent request inserted the same username/email between our
        # pre-check and commit; the unique constraint rejected this row.
        await db.rollback()
        raise UserAlreadyExistsError("username or email")
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, identifier: str, password: str) -> User:
    """Return the user matching ``identifier`` (email *or* username) and ``password``.

    The password is checked against the stored bcrypt hash. A missing user and a
    wrong password raise the *same* error, so the response cannot be used to
    discover which usernames or emails exist.

    Raises:
        InvalidCredentialsError: if no user matches or the password is wrong.
    """
    result = await db.execute(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    )
    user = result.scalar_one_or_none()
    # A user with no password_hash is a Google-only account: it can never be
    # authenticated by password, so treat it like a missing user.
    if user is None or not user.password_hash or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return user


async def _generate_unique_username(db: AsyncSession, email: str) -> str:
    """Derive a unique, schema-valid username from an email address.

    Uses the email's local part, stripped to the allowed character set, and
    appends an incrementing suffix until the username is free. Guarantees a
    result of 3–50 characters matching ``^[A-Za-z0-9_]+$``.
    """
    base = re.sub(r"[^A-Za-z0-9_]", "", email.split("@")[0]) or "user"
    if len(base) < 3:
        base = f"{base}user"
    base = base[:40]  # leave headroom for a numeric suffix within the 50-char limit

    candidate, suffix = base, 0
    while (
        await db.execute(select(User.user_id).where(User.username == candidate))
    ).first() is not None:
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


async def authenticate_google_user(db: AsyncSession, credential: str) -> User:
    """Resolve a Google ID token to a local user, creating or linking as needed.

    The credential is verified with Google first, then mapped to an account in
    priority order:

    1. An account already linked to this Google id — returned as-is.
    2. An existing account with the same (Google-verified) email — linked by
       storing the Google id, so password and Google sign-in reach one account.
    3. Otherwise a fresh password-less account with a generated username.

    Linking by email is gated on Google's ``email_verified`` flag to prevent a
    spoofed email from hijacking an existing account.

    Raises:
        GoogleAuthError: if the token is invalid or an unverified email collides
            with an existing account.
    """
    claims = await verify_google_id_token(credential)
    google_sub = claims["sub"]
    email = claims["email"]
    email_verified = claims.get("email_verified", False)

    linked = await db.execute(select(User).where(User.google_id == google_sub))
    user = linked.scalar_one_or_none()
    if user is not None:
        return user

    by_email = await db.execute(select(User).where(User.email == email))
    user = by_email.scalar_one_or_none()
    if user is not None:
        if not email_verified:
            raise GoogleAuthError("Google email is not verified; cannot link account.")
        user.google_id = google_sub
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        username=await _generate_unique_username(db, email),
        email=email,
        google_id=google_sub,
        password_hash=None,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent first-time sign-in for the same Google account: re-read the
        # row the other request committed instead of failing.
        await db.rollback()
        existing = await db.execute(select(User).where(User.google_id == google_sub))
        user = existing.scalar_one_or_none()
        if user is None:
            raise GoogleAuthError("Could not create account from Google sign-in.")
    else:
        await db.refresh(user)
    return user
