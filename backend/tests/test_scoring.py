"""Scoring behaviour for the job feed.

Guards the two things that make profile-derived ranking work: 2-letter domain
terms must count, and a title that only brushes a term must rank far below a
genuine match once the description and technologies are considered.
"""

from app.services.score_service import _tokenize, keyword_score


def test_two_letter_domain_terms_survive_tokenization():
    """The whole point of the {2,} tokenizer: AI/ML/Go/QA must not be dropped."""
    tokens = _tokenize("AI ML Go QA UX Backend Engineer")
    assert {"ai", "ml", "go", "qa", "ux", "backend", "engineer"} <= tokens


def test_two_letter_function_words_are_still_filtered():
    """{2,} would admit noise words; the stopword set must remove them."""
    tokens = _tokenize("Backend Engineer in the US or at an AI team")
    assert "ai" in tokens and "backend" in tokens
    assert not ({"in", "or", "at", "an", "us"} & tokens)


def test_ai_only_title_scores_far_below_a_real_engineering_match():
    """'AI Compliance Officer' brushes 'ai' but nothing else; a backend role hits
    role terms in the title AND technologies in the description."""
    roles = ["Backend Engineer", "AI Engineer", "ML Engineer"]
    techs = ["python", "fastapi", "postgresql"]

    junk = keyword_score(
        title="AI Compliance Officer",
        description="Ensure responsible AI governance and regulatory compliance.",
        search_terms=roles,
        resume_skills=techs,
    )
    real = keyword_score(
        title="Senior Backend Engineer",
        description="Build backend services in Python with FastAPI and PostgreSQL.",
        search_terms=roles,
        resume_skills=techs,
    )
    assert real > junk
    assert real - junk >= 30  # decisively demoted, not marginally


def test_description_lifts_a_matching_role_over_a_title_only_brush():
    """Two jobs, same weak title signal — the one whose description matches wins."""
    roles = ["Backend Engineer"]
    techs = ["python", "django"]
    with_desc = keyword_score(
        "Software Engineer", "Backend engineer working in Python and Django.", roles, techs
    )
    without = keyword_score(
        "Software Engineer", "Front-of-house customer success role.", roles, techs
    )
    assert with_desc > without


def test_no_terms_yields_zero():
    """A user with no roles and no override scores nothing → empty feed."""
    assert (
        keyword_score("Backend Engineer", "python", search_terms=[], resume_skills=["python"]) == 0
    )
