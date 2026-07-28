"""Validation for deployment-tunable ATS ingestion controls."""

import pytest
from pydantic import ValidationError

from app.config import Settings

_REQUIRED_SETTINGS = {
    "database_url": "postgresql+asyncpg://postgres:postgres@localhost/test",
    "secret_key": "test-secret",
}


def test_ats_response_size_property_uses_megabytes():
    configured = Settings(**_REQUIRED_SETTINGS, ats_max_response_mb=2)

    assert configured.ats_max_response_bytes == 2 * 1024 * 1024


@pytest.mark.parametrize(
    "override",
    [
        {"ats_http_timeout_seconds": 0},
        {"ats_max_response_mb": 0},
        {"ats_max_attempts": 0},
        {"ats_global_concurrency": 0},
        {"ats_http_max_connections": 0},
    ],
)
def test_ats_operational_settings_reject_nonpositive_values(override: dict):
    with pytest.raises(ValidationError):
        Settings(**_REQUIRED_SETTINGS, **override)


def test_keepalive_pool_cannot_exceed_total_connections():
    with pytest.raises(ValidationError, match="keepalive_connections"):
        Settings(
            **_REQUIRED_SETTINGS,
            ats_http_max_connections=5,
            ats_http_max_keepalive_connections=6,
        )
