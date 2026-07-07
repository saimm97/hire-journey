"""LLM-powered job evaluation agent.

Runs the evaluation as a single structured LLM call, producing a match score
plus actionable strengths, weaknesses, and recommendations calibrated to the
specific candidate-job pair. Provider selection and retries are handled by
:mod:`app.utils.llm`.
"""

from pydantic import BaseModel, Field

from app.utils import llm

_SYSTEM_PROMPT = """\
You are an expert technical recruiter and career coach evaluating how well a \
candidate's background fits a specific job posting.

You receive:
1. The candidate's resume (skills list + raw text)
2. The full job description

Produce a rigorous, evidence-based evaluation. Reference concrete skills, \
projects, and experience from the resume. Never make up credentials.

Scoring guide for match_score (0–100):
  90–100  Near-perfect fit — candidate exceeds almost all requirements
  70–89   Strong match — most requirements met, minor gaps only
  50–69   Partial match — core requirements met, real gaps exist
  30–49   Weak match — several significant gaps, worth applying only if motivated
  0–29    Poor fit — major blockers, do not recommend applying

For strengths: name 3–5 specific, role-relevant things the candidate brings.
  Good: "Production FastAPI experience (2 projects) directly matches the Python \
backend requirement"
  Bad: "Has Python experience"

For weaknesses: name 2–4 genuine gaps that would concern a hiring manager.
  Good: "No Kubernetes experience — the JD lists K8s as a hard requirement"
  Bad: "Could improve on some areas"

For recommendations: give 3–5 specific, actionable steps to improve this application.
  Good: "Add a bullet in the FastAPI project describing throughput numbers — the \
JD asks for experience with high-load systems"
  Bad: "Tailor your resume"

Be honest. An honest weak evaluation is more valuable than a falsely positive one.
"""


class EvaluationResult(BaseModel):
    match_score: int = Field(
        ge=0, le=100,
        description="Overall fit score 0-100 per the scoring guide",
    )
    strengths: list[str] = Field(
        min_length=1, max_length=8,
        description="3-5 specific strengths the candidate brings to this role",
    )
    weaknesses: list[str] = Field(
        min_length=1, max_length=6,
        description="2-4 genuine gaps or concerns a hiring manager would flag",
    )
    recommendations: list[str] = Field(
        min_length=1, max_length=8,
        description="3-5 specific, actionable steps to strengthen this application",
    )


def _build_user_message(
    resume_text: str,
    skills: list[str],
    job_title: str,
    company: str,
    location: str | None,
    description: str,
) -> str:
    skills_line = ", ".join(skills) if skills else "See resume"
    loc = location or "Not specified"
    return (
        f"CANDIDATE SKILLS: {skills_line}\n\n"
        f"CANDIDATE RESUME:\n{resume_text}\n\n"
        f"---\n\n"
        f"JOB: {job_title} at {company} ({loc})\n\n"
        f"JOB DESCRIPTION:\n{description}"
    )


async def evaluate_job(
    resume_text: str,
    skills: list[str],
    job_title: str,
    company: str,
    location: str | None,
    description: str,
) -> EvaluationResult:
    """Run the LLM evaluation. Raises ExtractionError if extraction fails."""
    user = _build_user_message(resume_text, skills, job_title, company, location, description)
    return await llm.structured_extract(_SYSTEM_PROMPT, user, EvaluationResult, temperature=0.3)
