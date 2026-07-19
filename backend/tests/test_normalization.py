"""Tests for lenient date and URL normalization of LLM-extracted values."""

from datetime import date

import pytest

from app.utils.normalization import normalize_month, normalize_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2021-05", date(2021, 5, 1)),
        ("2021-5", date(2021, 5, 1)),
        ("2021/05", date(2021, 5, 1)),
        ("2021", date(2021, 1, 1)),
        ("May 2021", date(2021, 5, 1)),
        ("January 2021", date(2021, 1, 1)),
        ("Sep. 2021", date(2021, 9, 1)),
        ("Present", None),
        ("current", None),
        ("ongoing", None),
        ("", None),
        (None, None),
        ("garbage", None),
        ("2021-13", None),
        ("2021-00", None),
        ("1800-01", None),
        ("Smarch 2021", None),
    ],
)
def test_normalize_month(raw, expected):
    assert normalize_month(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://github.com/aneeb", "https://github.com/aneeb"),
        ("http://example.com", "http://example.com"),
        ("github.com/aneeb", "https://github.com/aneeb"),
        ("www.linkedin.com/in/aneeb", "https://www.linkedin.com/in/aneeb"),
        ("portfolio.dev", "https://portfolio.dev"),
        ("  github.com/aneeb  ", "https://github.com/aneeb"),
        ("not a url", None),
        ("aneeb", None),
        ("https://", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected
