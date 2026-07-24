"""Shared LLM plumbing: provider fallback plus schema-validated extraction.

Providers are built from every configured API key in priority order
(Groq -> Gemini -> OpenAI). ``structured_extract`` forces the model into
tool-calling against the given Pydantic schema and returns a validated
instance, retrying with the validation error fed back into the prompt.
"""

import logging
from typing import TypeVar

from pydantic import BaseModel

from app import messages
from app.config import settings
from app.exceptions import ExtractionError, LLMNotConfiguredError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def build_providers(temperature: float = 0.0) -> list:
    """Instantiate a chat model per configured key, in fallback priority order."""
    providers = []
    if settings.groq_api_key:
        from langchain_groq import ChatGroq

        providers.append(
            ChatGroq(
                model=settings.groq_model,
                temperature=temperature,
                api_key=settings.groq_api_key,
            )
        )
    if settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        providers.append(
            ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                temperature=temperature,
                google_api_key=settings.gemini_api_key,
            )
        )
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        providers.append(
            ChatOpenAI(
                model=settings.openai_model,
                temperature=temperature,
                api_key=settings.openai_api_key,
            )
        )
    return providers


async def structured_extract(
    system: str,
    user: str,
    schema: type[T],
    *,
    temperature: float = 0.0,
    retries: int = 2,
) -> T:
    """Call the LLM and return a schema-valid instance, retrying on failure.

    Raises LLMNotConfiguredError if no provider key is set, or ExtractionError
    if no provider returns valid data within the retry budget.
    """
    providers = build_providers(temperature)
    if not providers:
        raise LLMNotConfiguredError(messages.LLM_NOT_CONFIGURED)

    human = user
    last_error: Exception | None = None
    for _ in range(retries + 1):
        for provider in providers:
            try:
                result = await provider.with_structured_output(schema).ainvoke(
                    [("system", system), ("human", human)]
                )
            except Exception as exc:
                last_error = exc
                continue
            # Some providers (notably Gemini) can yield None instead of raising.
            if result is not None:
                return result
            last_error = ValueError("provider returned no structured output")
        human = (
            f"{user}\n\nYour previous response was invalid ({last_error}). "
            "Return ONLY valid data conforming to the schema."
        )

    # Log the provider error internally; the exception message reaches the user,
    # so it must not carry raw provider/exception text.
    logger.warning("Structured extraction exhausted retries; last error: %r", last_error)
    raise ExtractionError(messages.EXTRACTION_FAILED)
