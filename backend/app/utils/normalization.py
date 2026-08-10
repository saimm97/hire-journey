"""Deterministic cleanup of values before persistence.

The extraction schemas accept whatever the model produced; these helpers turn
that into database-ready values. Anything unrecognizable becomes None — the
raw extraction is preserved in ``resumes.parsed_content`` regardless.

``clean`` and ``clip`` also serve the user-edited paths, so they live here
rather than inside any one persistence module.
"""

from datetime import date

from app.utils import patterns


def clean(value: str | None) -> str | None:
    """Trimmed string, with blank collapsing to None."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def clip(value: str | None, limit: int) -> str | None:
    """Lenient-path guard: LLM output is unbounded but the columns are not.

    Truncates instead of erroring — a 500 on a valid resume is worse than a
    shortened value the user can fix in the editor.
    """
    cleaned = clean(value)
    return cleaned[:limit] if cleaned else None


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip


def normalize_month(value: str | None) -> date | None:
    """Lenient resume date -> first-of-month date, or None.

    Accepts YYYY-MM, bare YYYY (January assumed), and "May 2021"-style values.
    Present/current markers and anything unparseable become None.
    """
    if not value:
        return None
    value = value.strip()
    if patterns.PRESENT_RE.match(value):
        return None
    if match := patterns.ISO_MONTH_RE.match(value):
        year, month = int(match[1]), int(match[2])
    elif match := patterns.YEAR_ONLY_RE.match(value):
        year, month = int(match[1]), 1
    elif match := patterns.MONTH_NAME_RE.match(value):
        month_name = match[1][:3].lower()
        if month_name not in _MONTHS:
            return None
        year, month = int(match[2]), _MONTHS[month_name]
    else:
        return None
    if not (1 <= month <= 12 and 1900 <= year <= 2100):
        return None
    return date(year, month, 1)


def normalize_url(value: str | None) -> str | None:
    """Lenient URL cleanup: prepend https:// to bare domains, drop garbage."""
    if not value:
        return None
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value if patterns.DOMAIN_LIKE_RE.match(value.split("://", 1)[1]) else None
    if patterns.DOMAIN_LIKE_RE.match(value):
        return f"https://{value}"
    return None
