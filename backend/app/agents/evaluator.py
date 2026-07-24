"""LLM-powered job evaluation agent.

Ports the evaluation logic into a single structured
LangChain call. Produces a match score plus actionable strengths, weaknesses,
and recommendations calibrated to the specific candidate–job pair.

Provider priority (first configured key wins, then falls back in order):
  1. Groq  — llama-3.3-70b-versatile (fast, free tier)
  2. Gemini — gemini-2.0-flash
  3. OpenAI — gpt-4o-mini
"""

from pydantic import BaseModel, Field

from app.config import settings

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
        ge=0,
        le=100,
        description="Overall fit score 0-100 per the scoring guide",
    )
    strengths: list[str] = Field(
        min_length=1,
        max_length=8,
        description="3-5 specific strengths the candidate brings to this role",
    )
    weaknesses: list[str] = Field(
        min_length=1,
        max_length=6,
        description="2-4 genuine gaps or concerns a hiring manager would flag",
    )
    recommendations: list[str] = Field(
        min_length=1,
        max_length=8,
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


def _build_providers() -> list:
    """Return LLM instances for every configured provider, in priority order."""
    providers = []
    if settings.groq_api_key:
        from langchain_groq import ChatGroq

        providers.append(
            ChatGroq(
                model=settings.groq_model,
                temperature=0.3,
                api_key=settings.groq_api_key,
            )
        )
    if settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        providers.append(
            ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                temperature=0.3,
                google_api_key=settings.gemini_api_key,
            )
        )
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        providers.append(
            ChatOpenAI(
                model=settings.openai_model,
                temperature=0.3,
                api_key=settings.openai_api_key,
            )
        )
    return providers


async def evaluate_job(
    resume_text: str,
    skills: list[str],
    job_title: str,
    company: str,
    location: str | None,
    description: str,
) -> EvaluationResult:
    """Run the LLM evaluation. Tries providers in order: Groq → Gemini → OpenAI.

    Raises RuntimeError if all configured providers fail or none are configured.
    """
    providers = _build_providers()
    if not providers:
        raise RuntimeError(
            "No LLM API key configured. Set GROQ_API_KEY, GEMINI_API_KEY, "
            "or OPENAI_API_KEY in .env"
        )

    messages = [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            _build_user_message(
                resume_text,
                skills,
                job_title,
                company,
                location,
                description,
            ),
        ),
    ]

    last_err: Exception | None = None
    for llm in providers:
        try:
            return await llm.with_structured_output(EvaluationResult).ainvoke(messages)
        except Exception as exc:
            last_err = exc

    raise RuntimeError(f"All LLM providers failed. Last error: {last_err}") from last_err
