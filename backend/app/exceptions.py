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


class DocumentParseError(Exception):
    """An uploaded document could not be read as text (unsupported, corrupt, or empty)."""


class ExtractionError(Exception):
    """The LLM could not return schema-valid structured data, or none is configured."""
