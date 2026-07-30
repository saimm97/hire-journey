"""Contract tests for safe, machine-readable ingestion reports."""

import pytest

from app.services.ingestion_report import (
    IngestionIssue,
    IssueCode,
    IssueStage,
    sanitize_feed_url,
)


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (
            "https://operator:private-token@boards-api.greenhouse.io:443/"
            "v1/boards/example/jobs?content=true#fragment",
            "https://boards-api.greenhouse.io:443/v1/boards/example/jobs",
        ),
        (
            "http://internal.example.test:8080/boards/example?token=private",
            "http://internal.example.test:8080/boards/example",
        ),
        ("not-a-url", None),
        ("", None),
        (None, None),
    ],
)
def test_feed_urls_are_sanitized_for_operator_reports(configured, expected):
    assert sanitize_feed_url(configured) == expected


def test_issue_objects_enforce_the_sanitized_url_invariant():
    issue = IngestionIssue(
        stage=IssueStage.FETCH,
        code=IssueCode.REQUEST_TIMEOUT,
        message="The provider request timed out.",
        feed_url=(
            "https://operator:private@api.lever.co/v0/postings/example" "?token=private#fragment"
        ),
        retry_eligible=True,
    )

    assert issue.feed_url == "https://api.lever.co/v0/postings/example"
