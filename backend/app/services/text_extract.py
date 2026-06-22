"""Deterministic field extraction from CV text.

Contacts come from regex; name, skills, and summary from layout cues (the name
sits at the top, sections are introduced by recognisable headings). The helpers
here — section slicing, URL normalising, skill parsing — are shared with project
extraction. Empty results signal a layout these heuristics can't handle, i.e.
the point to fall back to LLM extraction.
"""

import re

from app.schemas.profile import CVExtraction

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[\w%-]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+(?:/[\w.-]+)?", re.I)
URL_RE = re.compile(r"https?://[^\s)\]]+", re.I)
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}")
NAME_RE = re.compile(r"^[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3}$")

SKILL_HEADINGS = {
    "skills", "technical skills", "tech stack", "technologies", "core competencies",
    "technical proficiencies", "tools and technologies", "tools & technologies",
}
SUMMARY_HEADINGS = {"summary", "professional summary", "profile", "objective", "about"}
PROJECT_HEADINGS = {
    "projects", "personal projects", "academic projects", "selected projects",
    "side projects", "notable projects", "key projects",
}
SECTION_HEADINGS = SKILL_HEADINGS | SUMMARY_HEADINGS | PROJECT_HEADINGS | {
    "experience", "work experience", "employment", "education", "certifications",
    "awards", "interests", "languages", "publications", "contact", "references",
    "achievements",
}

# Collapse runs of spaces (common in PDF text) into a delimiter, then split on the
# usual separators. This keeps multi-word skills ("Machine Learning") intact while
# breaking column/whitespace-aligned lists apart.
_WS_RUN_RE = re.compile(r"[ \t]{2,}")
_SKILL_SPLIT_RE = re.compile(r"[,;|/]+|[•·▪◦•]+")


def lines_of(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def extract_fields(text: str) -> CVExtraction:
    lines = lines_of(text)
    first, last = _name(lines)
    return CVExtraction(
        first_name=first,
        last_name=last,
        email=_match(EMAIL_RE, text),
        phone=_phone(text),
        linkedin_url=normalize_url(_match(LINKEDIN_RE, text)),
        github_url=normalize_url(_match(GITHUB_RE, text)),
        tech_stack=parse_skills(section_lines(lines, SKILL_HEADINGS)),
        summary=_section_text(lines, SUMMARY_HEADINGS),
    )


def section_lines(lines: list[str], headings: set[str]) -> list[str]:
    """Lines between a matching heading and the next known section heading."""
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


def parse_skills(lines: list[str]) -> list[str]:
    skills = []
    for line in lines:
        for part in _SKILL_SPLIT_RE.split(_WS_RUN_RE.sub(",", line)):
            token = _clean_skill(part)
            if token:
                skills.append(token)
    return skills


def normalize_url(raw: str | None) -> str | None:
    if not raw:
        return None
    url = raw.rstrip("/.,)")
    return url if url.lower().startswith("http") else f"https://{url}"


def _match(pattern: re.Pattern, text: str) -> str | None:
    found = pattern.search(text)
    return found.group(0) if found else None


def _phone(text: str) -> str | None:
    for candidate in PHONE_RE.findall(text):
        if sum(ch.isdigit() for ch in candidate) >= 7:
            return candidate.strip()
    return None


def _name(lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines[:10]:
        if EMAIL_RE.search(line) or any(ch.isdigit() for ch in line):
            continue
        if NAME_RE.match(line):
            parts = line.split()
            return parts[0], parts[-1]
    return None, None


def _clean_skill(token: str) -> str | None:
    token = token.strip().strip("•·▪◦-–*").strip()
    if ":" in token:  # drop a "Category:" label, keep the value
        token = token.rsplit(":", 1)[-1].strip()
    if not token or not any(ch.isalpha() for ch in token):
        return None
    if len(token) > 40 or len(token.split()) > 4:  # reject prose, keep skill-sized tokens
        return None
    return token


def _section_text(lines: list[str], headings: set[str]) -> str | None:
    return " ".join(section_lines(lines, headings)) or None
