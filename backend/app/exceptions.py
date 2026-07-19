"""Custom exceptions raised by the service layer.

Kept in one module so handlers import their failure cases from a single place
and the service files stay free of scattered exception definitions. The matching
user-facing messages live in :mod:`app.messages`.
"""


class UserAlreadyExistsError(Exception):
    """Registration hit a taken username or email."""

    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(field)


class InvalidCredentialsError(Exception):
    """The login identifier or password did not match an account."""


class GoogleAuthError(Exception):
    """Google sign-in could not be completed."""


class PdfUnreadableError(Exception):
    """The bytes could not be opened or read as a PDF."""


class PdfNoTextError(Exception):
    """The PDF opened but contained no extractable text."""


class DocumentParseError(Exception):
    """The uploaded document could not be read or contained no extractable text."""


class LLMNotConfiguredError(Exception):
    """No LLM provider API key is configured; extraction cannot run."""


class ExtractionError(Exception):
    """Every configured LLM provider failed to return schema-valid data."""
