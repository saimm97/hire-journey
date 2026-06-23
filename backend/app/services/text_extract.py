"""Identity-field extraction from CV text.

Thin wrapper over :mod:`app.utils.parsing`: it only maps shared parsing helpers
onto the CV schema. Empty results signal a layout these heuristics can't handle,
i.e. the point to fall back to LLM extraction.
"""

from app.schemas.profile import CVExtraction
from app.utils import parsing, patterns


def extract_fields(text: str) -> CVExtraction:
    lines = parsing.lines_of(text)
    first, last = parsing.extract_name(lines)
    return CVExtraction(
        first_name=first,
        last_name=last,
        email=parsing.parse_email(text),
        phone=parsing.extract_phone(text),
        linkedin_url=parsing.normalize_url(parsing.re_first(patterns.LINKEDIN_RE, text)),
        github_url=parsing.normalize_url(parsing.re_first(patterns.GITHUB_RE, text)),
        tech_stack=parsing.parse_skills(parsing.section_lines(lines, parsing.SKILL_HEADINGS)),
        summary=parsing.section_text(lines, parsing.SUMMARY_HEADINGS),
    )
