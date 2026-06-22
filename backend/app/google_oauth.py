"""Verification of Google ID tokens for Continue with Google."""

import asyncio

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app import messages
from app.config import settings


class GoogleAuthError(Exception):
    """Google sign-in could not be completed."""


async def verify_google_id_token(credential: str) -> dict:
    """Verify a Google ID token against our client id and return its claims."""
    if not settings.google_client_id:
        raise GoogleAuthError(messages.GOOGLE_NOT_CONFIGURED)
    try:
        claims = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise GoogleAuthError(messages.GOOGLE_TOKEN_INVALID) from exc
    if not claims.get("email"):
        raise GoogleAuthError(messages.GOOGLE_NO_EMAIL)
    return claims
