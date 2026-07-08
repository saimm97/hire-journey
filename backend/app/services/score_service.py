"""Keyword overlap scoring for bulk job ranking.

Scores each job 0–100 against keywords derived from the user's search terms and
resume skills. No LLM, no external calls — purely deterministic.

Scoring logic:
  - Title match = 3x weight, description match = 1x weight (a keyword in the
    title is a stronger signal than one buried in a long description).
  - The weighted match count is passed through a saturating curve, so matching a
    handful of your terms already scores high. Crucially, the score depends on
    HOW MANY of your terms a job matches — not what FRACTION of all your terms it
    covers — so listing more preferences no longer drags every score down.
  - Search terms drive the base (0–80); resume skills add a bonus (0–20).
"""

import math
import re

_STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "are", "you", "your",
    "our", "will", "have", "has", "not", "but", "from", "they", "their",
    "all", "can", "its", "was", "been", "one", "who", "may", "any", "use",
    # 2-letter noise words. Needed because the tokenizer keeps 2-char tokens so
    # domain terms like AI, ML, Go, QA, UX survive — those are intentionally NOT
    # listed here, so only the genuine function words below get filtered.
    "in", "to", "of", "or", "is", "at", "as", "by", "an", "be", "it",
    "on", "so", "if", "no", "up", "us", "we", "he", "me", "my", "do",
}

# Saturation constants: how many (weighted) matches it takes to approach the max.
# The curve is 1 - exp(-matches / SCALE), so a few strong matches already score
# high and the score never depends on the total number of terms searched.
# Higher = needs more matches to saturate.
_MATCH_SCALE = 8.0   # search-term matches (weighted: title×3 + description×1)
_SKILL_SCALE = 4.0   # resume-skill matches


def _tokenize(text: str) -> set[str]:
    return {
        w for w in re.findall(r"\b[a-z]{2,}\b", text.lower())
        if w not in _STOP_WORDS
    }


def keyword_score(
    title: str,
    description: str,
    search_terms: list[str],
    resume_skills: list[str] | None = None,
) -> int:
    """Return an integer score 0–100 for a job.

    Search terms are the primary signal — they define the base score (0–80).
    Resume skills add a bonus (0–20) for jobs that match the user's background
    even beyond what they explicitly searched for.

    Both are scored by a saturating curve on the match COUNT, so a rich profile
    (many terms/skills) is not penalised — matching several of them well scores
    high regardless of how many were listed.
    """
    search_tokens: set[str] = set()
    for term in search_terms:
        search_tokens |= _tokenize(term.lower())

    if not search_tokens:
        return 0

    title_tokens = _tokenize(title)
    desc_tokens = _tokenize(description)

    # --- Base score: search terms (0–80) ---
    # Weighted match count — title matches count 3×. Independent of len(terms).
    weighted = 3 * len(search_tokens & title_tokens) + len(search_tokens & desc_tokens)
    base = 80 * (1 - math.exp(-weighted / _MATCH_SCALE))

    # --- Bonus: resume skills (0–20) ---
    bonus = 0.0
    if resume_skills:
        skill_tokens: set[str] = set()
        for skill in resume_skills:
            skill_tokens |= _tokenize(skill.lower())
        if skill_tokens:
            skill_matches = len(skill_tokens & (title_tokens | desc_tokens))
            bonus = 20 * (1 - math.exp(-skill_matches / _SKILL_SCALE))

    return min(100, int(base + bonus))
