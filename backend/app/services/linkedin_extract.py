"""Identity-field extraction from a LinkedIn PDF export.

Reuses the same parsing helpers as the CV extractor; only the target headings
and output schema differ.
"""

from app.schemas.profile import LinkedInExtraction
from app.utils import parsing, patterns
from app.utils.headings import SKILL_HEADINGS, SUMMARY_HEADINGS


def extract_fields(text: str) -> LinkedInExtraction:
    lines = parsing.lines_of(text)
    first, last = parsing.extract_name(lines)
    return LinkedInExtraction(
        first_name=first,
        last_name=last,
        email=parsing.parse_email(text),
        phone=parsing.extract_phone(text),
        linkedin_url=parsing.normalize_url(parsing.re_first(patterns.LINKEDIN_RE, text)),
        tech_stack=parsing.parse_skills(parsing.section_lines(lines, SKILL_HEADINGS)),
        linkedin_summary=parsing.section_text(lines, SUMMARY_HEADINGS),
    )
