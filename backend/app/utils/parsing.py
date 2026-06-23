"""Shared text-parsing helpers used by every document extractor.

These functions are deliberately format-agnostic: they turn raw PDF text into
lines, blocks, and sections, and pull out contact details, skills, and URLs.
The CV, LinkedIn, and projects extractors all build on them — no extractor
redefines a helper that lives here. All regular expressions come from
:mod:`app.utils.patterns`.
"""

import re

from email_validator import EmailNotValidError, validate_email

from app.utils import patterns
from app.utils.headings import (
    PROJECT_HEADINGS,
    SECTION_HEADINGS,
    SKILL_HEADINGS,
    SUMMARY_HEADINGS,
)

__all__ = [
    "PROJECT_HEADINGS",
    "SECTION_HEADINGS",
    "SKILL_HEADINGS",
    "SUMMARY_HEADINGS",
]


def lines_of(text: str) -> list[str]:
    """Non-empty, stripped lines — used for field and heading detection."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def blocks_of(text: str) -> list[list[str]]:
    """Group lines into blank-line-delimited blocks.

    Blank lines are the most reliable record separator in CV and project
    listings, so callers that need to tell one entry from the next start here.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line:
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def re_first(pattern: re.Pattern, text: str) -> str | None:
    found = pattern.search(text)
    return found.group(0) if found else None


def section_lines(lines: list[str], headings: set[str]) -> list[str]:
    """Stripped lines between a matching heading and the next known section."""
    collected, collecting = [], False
    for line in lines:
        if line.lower().rstrip(":") in headings:
            collecting = True
            continue
        if collecting:
            if line.lower().rstrip(":") in SECTION_HEADINGS:
                break
            collected.append(line)
    return collected


def section_block(text: str, headings: set[str]) -> str:
    """Raw text (blank lines preserved) between a heading and the next section.

    Unlike :func:`section_lines`, this keeps the blank lines that separate
    records, so the projects extractor can split the section into entries.
    """
    out, collecting = [], False
    for raw in text.splitlines():
        key = raw.strip().lower().rstrip(":")
        if not collecting:
            if key in headings:
                collecting = True
            continue
        if key and key in SECTION_HEADINGS:
            break
        out.append(raw)
    return "\n".join(out).strip("\n")


def section_text(lines: list[str], headings: set[str]) -> str | None:
    return " ".join(section_lines(lines, headings)) or None


def parse_skills(lines: list[str]) -> list[str]:
    skills = []
    for line in lines:
        for part in patterns.SKILL_SPLIT_RE.split(patterns.WS_RUN_RE.sub(",", line)):
            token = _clean_skill(part)
            if token:
                skills.append(token)
    return skills


def normalize_url(raw: str | None) -> str | None:
    if not raw:
        return None
    url = raw.rstrip("/.,)")
    return url if url.lower().startswith("http") else f"https://{url}"


def extract_name(lines: list[str]) -> tuple[str | None, str | None]:
    """First and last name from the top lines (the name precedes any contacts)."""
    for line in lines[:10]:
        if patterns.EMAIL_RE.search(line) or any(ch.isdigit() for ch in line):
            continue
        if patterns.NAME_RE.match(line):
            parts = line.split()
            return parts[0], parts[-1]
    return None, None


def extract_phone(text: str) -> str | None:
    for candidate in patterns.PHONE_RE.findall(text):
        if sum(ch.isdigit() for ch in candidate) >= 7:
            return candidate.strip()
    return None


def parse_email(text: str) -> str | None:
    """Return the first syntactically valid email in the text, else ``None``."""
    match = patterns.EMAIL_RE.search(text)
    if not match:
        return None
    try:
        return validate_email(match.group(0), check_deliverability=False).normalized
    except EmailNotValidError:
        return None


def _clean_skill(token: str) -> str | None:
    token = token.strip().strip("•·▪◦-–*").strip()
    if ":" in token:
        token = token.rsplit(":", 1)[-1].strip()
    if not token or not any(ch.isalpha() for ch in token):
        return None
    if len(token) > 40 or len(token.split()) > 4:
        return None
    return token
