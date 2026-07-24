"""Title and location filtering applied after fetching raw jobs from ATS boards.

Pure functions — no DB, no I/O. Mirrors the logic in career-ops scan.mjs but in
Python. All comparisons are case-insensitive substring matches, exactly as career-ops
does them.
"""

from app.sources.base import RawJob


def passes_title_filter(title: str, positive: list[str], negative: list[str]) -> bool:
    t = title.lower()
    if any(kw.lower() in t for kw in negative):
        return False
    if not positive:
        return True
    return any(kw.lower() in t for kw in positive)


def passes_location_filter(location: str | None, allow: list[str], block: list[str]) -> bool:
    if not location:
        return True
    loc = location.lower()
    # Block list takes priority — a blocked location is rejected even if it matches allow
    if any(kw.lower() in loc for kw in block):
        return False
    if not allow:
        return True
    return any(kw.lower() in loc for kw in allow)


def apply_filters(
    jobs: list[RawJob],
    positive: list[str],
    negative: list[str],
    allow: list[str],
    block: list[str],
) -> list[RawJob]:
    return [
        j
        for j in jobs
        if passes_title_filter(j.title, positive, negative)
        and passes_location_filter(j.location, allow, block)
    ]
