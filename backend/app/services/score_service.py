"""Keyword overlap scoring for bulk job ranking.

Scores each job 0–100 against a set of keywords derived from the user's search
terms and resume skills. No LLM, no external calls — purely deterministic.

Scoring logic:
  - Title hit = 3x weight (a keyword in the job title is a stronger signal)
  - Description hit = 1x weight
  - Score = (weighted hits) / (max possible weighted hits), scaled to 0–100
  - Capped at 100 even if description adds hits beyond what title alone could score

This intentionally favours jobs where the user's keywords appear in the title,
which are almost always more relevant than jobs where they only appear buried in
a 500-word description.
"""

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

    Keeping them separate prevents resume skills from diluting the denominator
    and making all scores artificially low.
    """
    # --- Base score: search terms (0–80) ---
    search_tokens: set[str] = set()
    for term in search_terms:
        search_tokens |= _tokenize(term.lower())

    if not search_tokens:
        return 0

    title_tokens = _tokenize(title)
    desc_tokens = _tokenize(description)

    title_hits = len(search_tokens & title_tokens) * 3
    desc_hits = len(search_tokens & desc_tokens)
    max_possible = len(search_tokens) * 3

    base = int((title_hits + desc_hits) / max_possible * 80)

    # --- Bonus: resume skills (0–20) ---
    bonus = 0
    if resume_skills:
        skill_tokens: set[str] = set()
        for skill in resume_skills:
            skill_tokens |= _tokenize(skill.lower())
        if skill_tokens:
            skill_hits = len(skill_tokens & (title_tokens | desc_tokens))
            bonus = int(skill_hits / len(skill_tokens) * 20)

    return min(100, base + bonus)
