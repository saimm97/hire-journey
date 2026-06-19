"""Verification of Google ID tokens for the "Continue with Google" flow.

This is infrastructure, parallel to ``app.security``: it turns the opaque
credential the browser receives from Google Identity Services into a set of
trusted claims, or fails. It contains no user/database logic — that lives in the
service layer.
"""

import asyncio

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import settings


class GoogleAuthError(Exception):
    """Raised when a Google ID token is missing, invalid, or unverifiable."""


async def verify_google_id_token(credential: str) -> dict:
    """Verify a Google ID token and return its validated claims.

    Checks the token's signature against Google's published public keys and
    confirms it was minted for *our* OAuth client (the audience) and has not
    expired. ``verify_oauth2_token`` is a blocking call (it fetches/validates
    against Google's certs), so it runs in a worker thread to keep the event
    loop free.

    Raises:
        GoogleAuthError: if Google sign-in is not configured on the server, or
            the token is invalid, expired, or issued for another audience.
    """
    if not settings.google_client_id:
        raise GoogleAuthError("Google sign-in is not configured on the server.")
    try:
        claims = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        # Bad signature, wrong audience, expired, malformed token, etc.
        raise GoogleAuthError("Could not verify Google credential.") from exc

    if not claims.get("email"):
        raise GoogleAuthError("Google account did not provide an email address.")
    return claims
