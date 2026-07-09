"""User-facing strings and shared constants for the auth API."""

AUTH_HEADER = {"WWW-Authenticate": "Bearer"}

CREDENTIALS_INVALID = "Incorrect username/email or password."
CREDENTIALS_UNVERIFIED = "Could not validate credentials."

GOOGLE_NOT_CONFIGURED = "Google sign-in is not configured on the server."
GOOGLE_TOKEN_INVALID = "Could not verify Google credential."
GOOGLE_NO_EMAIL = "Google account did not provide an email address."
GOOGLE_EMAIL_UNVERIFIED = "Google email is not verified; cannot link account."
GOOGLE_ACCOUNT_FAILED = "Could not create account from Google sign-in."


PROFILE_NOT_FOUND = "No profile yet. Upload a CV to get started."

PDF_REQUIRED = "Uploaded file must be a PDF."
PDF_UNREADABLE = "The PDF could not be read; it may be corrupt or password-protected."
PDF_NO_TEXT = "No text could be extracted from the PDF (scanned images are not supported)."


def already_registered(field: str) -> str:
    return f"That {field} is already registered."


def file_too_large(max_mb: int) -> str:
    return f"File exceeds the maximum size of {max_mb} MB."
