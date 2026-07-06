"""Shared LLM plumbing: provider fallback plus schema-validated extraction.

Providers are built from the first configured API key in priority order
(Groq -> Gemini -> OpenAI). ``structured_extract`` returns a validated Pydantic
model, retrying with the validation error fed back into the prompt.
"""

from pydantic import BaseModel

from app.config import settings
from app.exceptions import ExtractionError


def build_providers(temperature: float = 0.0) -> list:
    providers = []
    if settings.groq_api_key:
        from langchain_groq import ChatGroq

        providers.append(ChatGroq(
            model=settings.groq_model, temperature=temperature, api_key=settings.groq_api_key,
        ))
    if settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        providers.append(ChatGoogleGenerativeAI(
            model=settings.gemini_model, temperature=temperature, google_api_key=settings.gemini_api_key,
        ))
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        providers.append(ChatOpenAI(
            model=settings.openai_model, temperature=temperature, api_key=settings.openai_api_key,
        ))
    return providers


async def structured_extract(
    system: str,
    user: str,
    schema: type[BaseModel],
    *,
    temperature: float = 0.0,
    retries: int = 2,
) -> BaseModel:
    """Call the LLM and return a schema-valid instance, retrying on failure.

    Raises ExtractionError if no provider is configured or none returns valid
    data within the retry budget.
    """
    providers = build_providers(temperature)
    if not providers:
        raise ExtractionError(
            "No LLM API key configured. Set GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY."
        )

    human = user
    last_error: Exception | None = None
    for _ in range(retries + 1):
        for llm in providers:
            try:
                return await llm.with_structured_output(schema).ainvoke(
                    [("system", system), ("human", human)]
                )
            except Exception as exc:
                last_error = exc
        human = (
            f"{user}\n\nYour previous response was invalid ({last_error}). "
            "Return ONLY valid JSON that conforms to the schema."
        )

    raise ExtractionError(f"LLM failed to return valid data after retries: {last_error}")
