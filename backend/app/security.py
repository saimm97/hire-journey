"""Low-level security primitives: password hashing and JWT creation.

This module is infrastructure, not business logic. It knows nothing about the
database or HTTP layer — it only turns plaintext into hashes and subjects into
signed tokens. Business rules (uniqueness checks, lookups) live in the service
layer; request/response handling lives in the API layer.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

# bcrypt only ever hashes the first 72 bytes of input and raises on anything
# longer (since bcrypt 5.x). We truncate to that boundary so callers never hit a
# runtime error regardless of how long a password the user submits.
_BCRYPT_MAX_BYTES = 72


def _encode_password(password: str) -> bytes:
    """Encode a plaintext password to the byte form bcrypt expects.

    Truncates to bcrypt's 72-byte working limit so longer inputs hash instead of
    raising. Truncation is applied identically on hash and verify, so the limit
    is invisible to callers.
    """
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt and return it as a UTF-8 string.

    The returned value (algorithm, cost, salt and digest) is self-contained and
    safe to store in the ``users.password_hash`` column.
    """
    digest = bcrypt.hashpw(_encode_password(password), bcrypt.gensalt())
    return digest.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if ``plain_password`` matches the stored bcrypt ``password_hash``.

    Returns False (rather than raising) on a malformed stored hash so a corrupt
    row can never be used to bypass authentication.
    """
    try:
        return bcrypt.checkpw(_encode_password(plain_password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for ``subject`` (the user id).

    The subject is stored in the standard ``sub`` claim and an ``exp`` expiry is
    added. Token lifetime defaults to ``settings.access_token_expire_minutes``
    when ``expires_delta`` is not supplied.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    claims = {"sub": subject, "exp": expire}
    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)
