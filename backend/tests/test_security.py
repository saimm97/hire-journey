"""Tests for the password-hashing and JWT helpers."""

import jwt

from app.config import settings
from app.security import create_access_token, hash_password, verify_password


def test_hash_is_not_plaintext_and_is_salted():
    first = hash_password("hunter2-secret")
    second = hash_password("hunter2-secret")
    assert first != "hunter2-secret"
    assert first != second


def test_verify_accepts_correct_and_rejects_wrong_password():
    digest = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", digest) is True
    assert verify_password("wrong password", digest) is False


def test_verify_handles_overlong_password():
    long_password = "a" * 200
    assert verify_password(long_password, hash_password(long_password)) is True


def test_verify_returns_false_for_malformed_hash():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_access_token_round_trips_subject():
    token = create_access_token(subject="user-123")
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "user-123"
    assert "exp" in payload
