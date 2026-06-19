"""Unit tests for the password-hashing and JWT primitives in app.security.

These exercise the security layer in isolation — no database or HTTP server is
needed, so they run fast and pin down the behaviour the auth flow relies on.
"""

import jwt

from app.config import settings
from app.security import create_access_token, hash_password, verify_password


def test_hash_is_not_plaintext_and_is_salted():
    """Hashing must obscure the password and use a fresh salt each call."""
    first = hash_password("hunter2-secret")
    second = hash_password("hunter2-secret")
    assert first != "hunter2-secret"
    assert first != second  # different salts -> different digests


def test_verify_accepts_correct_and_rejects_wrong_password():
    """A round-trip verifies, a wrong password does not."""
    digest = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", digest) is True
    assert verify_password("wrong password", digest) is False


def test_verify_handles_overlong_password_without_crashing():
    """Passwords beyond bcrypt's 72-byte limit hash and verify, not error."""
    long_password = "a" * 200
    digest = hash_password(long_password)
    assert verify_password(long_password, digest) is True


def test_verify_returns_false_for_malformed_hash():
    """A corrupt stored hash must fail closed (False), never raise."""
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_access_token_round_trips_subject():
    """The subject we sign is the subject we read back from the decoded token."""
    token = create_access_token(subject="user-123")
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "user-123"
    assert "exp" in payload
