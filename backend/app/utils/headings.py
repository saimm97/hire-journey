"""Section heading sets used by every document extractor.

All heading comparisons are performed on lowercased, colon-stripped text, so
entries here must be lowercase with no trailing colon.
"""

SKILL_HEADINGS: set[str] = {
    "skills", "top skills", "technical skills", "tech stack", "technologies",
    "core competencies", "technical proficiencies", "tools and technologies",
    "tools & technologies",
}

SUMMARY_HEADINGS: set[str] = {
    "summary", "professional summary", "profile", "objective", "about",
}

PROJECT_HEADINGS: set[str] = {
    "projects", "personal projects", "academic projects", "selected projects",
    "side projects", "notable projects", "key projects",
}

SECTION_HEADINGS: set[str] = SKILL_HEADINGS | SUMMARY_HEADINGS | PROJECT_HEADINGS | {
    "experience", "work experience", "employment", "education", "certifications",
    "awards", "interests", "languages", "publications", "contact", "references",
    "achievements",
}
